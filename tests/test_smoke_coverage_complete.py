"""Complete deterministic smoke validation and failure accounting coverage."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import smoke
from agency_runtime.core.installer import install_agent_adapter


def test_check_records_exceptions_without_losing_type() -> None:
    result = smoke._check("failure", lambda: (_ for _ in ()).throw(ValueError("bad")))
    assert result == {"name": "failure", "status": "fail", "error": "ValueError: bad"}


def test_prepare_fake_home_covers_every_host_and_unknown(tmp_path: Path) -> None:
    for host, relative in (
        ("hermes", Path(".hermes/plugins")),
        ("openclaw", Path(".openclaw")),
        ("codex", Path(".codex")),
        ("claude", Path(".claude")),
    ):
        home = tmp_path / host
        smoke._prepare_fake_host_home(home, host)
        assert (home / relative).is_dir()
    unknown = tmp_path / "unknown"
    smoke._prepare_fake_host_home(unknown, "unknown")
    assert not unknown.exists()


def _openclaw_bundle(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    (home / ".openclaw").mkdir(parents=True)
    result = install_agent_adapter("openclaw", home_dir=home)
    assert result["ok"] is True
    return home, Path(result["plugin_path"])


def test_openclaw_smoke_rejects_missing_and_invalid_manifests(
    tmp_path: Path,
    private_installer_launcher,
) -> None:
    _home, plugin = _openclaw_bundle(tmp_path / "missing")
    (plugin.parent / "package.json").unlink()
    with pytest.raises(RuntimeError, match="missing OpenClaw"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)

    _home, plugin = _openclaw_bundle(tmp_path / "id")
    manifest = plugin.parent / "openclaw.plugin.json"
    manifest.write_text('{"id":"wrong"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest id"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)

    _home, plugin = _openclaw_bundle(tmp_path / "extension")
    package = plugin.parent / "package.json"
    package.write_text('{"openclaw":{"extensions":[]}}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="extension entry"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)


def test_openclaw_smoke_rejects_missing_and_forbidden_bridge_tokens(
    tmp_path: Path,
    private_installer_launcher,
) -> None:
    _home, plugin = _openclaw_bundle(tmp_path / "tokens")
    plugin.write_text("const empty = true;", encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing tokens"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)

    _home, plugin = _openclaw_bundle(tmp_path / "forbidden")
    plugin.write_text(plugin.read_text(encoding="utf-8") + "\nspawnSync();\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="forbidden bridge tokens"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)


def test_openclaw_node_probe_handles_unrunnable_and_invalid_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher,
) -> None:
    _home, plugin = _openclaw_bundle(tmp_path / "node")
    node = tmp_path / ("node.exe" if os.name == "nt" else "node-bin")
    node.write_bytes(b"test node launcher")
    node.chmod(0o700)
    monkeypatch.delenv("AGENCY_CI_NODE", raising=False)
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: str(node))
    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unrunnable")),
    )
    result = smoke._smoke_openclaw_plugin("openclaw", plugin)
    assert result["syntax_check"] == "skipped: node not runnable (OSError)"

    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="syntax bad", stdout=""),
    )
    with pytest.raises(RuntimeError, match="syntax bad"):
        smoke._smoke_openclaw_plugin("openclaw", plugin)


def test_openclaw_node_probe_prefers_private_ci_node(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher,
) -> None:
    _home, plugin = _openclaw_bundle(tmp_path / "private-node")
    private_node = tmp_path / ("private-node.exe" if os.name == "nt" else "private-node-bin")
    private_node.write_bytes(b"private node launcher")
    private_node.chmod(0o700)
    fallback = tmp_path / ("fallback.exe" if os.name == "nt" else "fallback-node")
    fallback.write_bytes(b"fallback node launcher")
    fallback.chmod(0o700)
    launched: list[str] = []

    def run(argv, **_kwargs):
        launched.extend(argv)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setenv("AGENCY_CI_NODE", str(private_node))
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: str(fallback))
    monkeypatch.setattr(smoke.subprocess, "run", run)

    result = smoke._smoke_openclaw_plugin("openclaw", plugin)

    assert result["syntax_check"] == "passed"
    assert Path(launched[0]).resolve(strict=True) == private_node.resolve(strict=True)


def _marketplace_bundle(tmp_path: Path, host: str = "codex") -> tuple[Path, Path]:
    home = tmp_path / "home"
    (home / f".{host}").mkdir(parents=True)
    result = install_agent_adapter(host, home_dir=home)
    assert result["ok"] is True
    return home, Path(result["plugin_path"])


def test_installed_launcher_manifest_rejects_invalid_shapes_and_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher,
) -> None:
    frozen = smoke.snapshot_persistent_artifacts(private_installer_launcher)

    monkeypatch.setattr(smoke, "_load_plugin_json", lambda *_args, **_kwargs: [])
    with pytest.raises(RuntimeError, match="install manifest is invalid"):
        smoke._installed_launcher_paths(tmp_path)

    monkeypatch.setattr(
        smoke,
        "_load_plugin_json",
        lambda *_args, **_kwargs: {"artifacts": "invalid"},
    )
    with pytest.raises(RuntimeError, match="launcher identity is invalid"):
        smoke._installed_launcher_paths(tmp_path)

    monkeypatch.setattr(
        smoke,
        "_load_plugin_json",
        lambda *_args, **_kwargs: {"artifacts": [frozen[0].manifest()]},
    )
    with pytest.raises(RuntimeError, match="bind two artifacts"):
        smoke._installed_launcher_paths(tmp_path)

    monkeypatch.setattr(
        smoke,
        "_load_plugin_json",
        lambda *_args, **_kwargs: {"artifacts": [item.manifest() for item in frozen]},
    )
    monkeypatch.setattr(smoke, "snapshot_persistent_artifacts", lambda _paths: ())
    with pytest.raises(RuntimeError, match="changed after installation"):
        smoke._installed_launcher_paths(tmp_path)


def test_marketplace_smoke_reports_shallow_plugin_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugin-root"
    hooks_path = plugin_root / "hooks" / "hooks.json"
    mcp_path = plugin_root / ".mcp.json"
    skill_path = plugin_root / "skills" / "agency" / "SKILL.md"
    hooks_path.parent.mkdir(parents=True)
    skill_path.parent.mkdir(parents=True)
    hooks_path.write_text("{}", encoding="utf-8")
    mcp_path.write_text("{}", encoding="utf-8")
    skill_path.write_text(
        "agency.host_status agency.host_control runtime_control_generation expected_generation",
        encoding="utf-8",
    )

    def load(_path: object, *, label: str) -> dict[str, Any]:
        if label.endswith("plugin manifest"):
            return {"name": "agency-preflight"}
        if label.endswith("hooks manifest"):
            return {"hooks": {"UserPromptSubmit": []}}
        return {"mcpServers": {"agency-runtime": {"args": []}}}

    class ShallowParents:
        def __getitem__(self, index: int) -> Path:
            if index == 1:
                return plugin_root
            raise IndexError(index)

    shallow = SimpleNamespace(parents=ShallowParents())
    monkeypatch.setattr(smoke, "_load_plugin_json", load)

    with pytest.raises(RuntimeError, match="outside its marketplace layout"):
        smoke._smoke_marketplace_bundle("claude", shallow)  # type: ignore[arg-type]


def test_marketplace_smoke_rejects_manifest_layout_and_hooks(
    tmp_path: Path,
    private_installer_launcher,
) -> None:
    _home, manifest = _marketplace_bundle(tmp_path / "name")
    manifest.write_text('{"name":"wrong"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest name"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "layout")
    (manifest.parents[1] / "hooks" / "hooks.json").unlink()
    with pytest.raises(RuntimeError, match="missing hooks"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "hook")
    hooks = manifest.parents[1] / "hooks" / "hooks.json"
    hooks.write_text('{"hooks":{}}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="UserPromptSubmit"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "missing-declaration")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.pop("hooks", None)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not declare"):
        smoke._smoke_marketplace_bundle("codex", manifest)


@pytest.mark.parametrize(
    ("corruption", "message"),
    [
        ("extra_event", "event set"),
        ("registration", "registration is invalid"),
        ("handler", "command handler is invalid"),
        ("timeout_sec", "unsupported input key timeoutSec"),
        ("timeout_bool", "timeout is invalid"),
        ("timeout_text", "timeout is invalid"),
        ("timeout_zero", "timeout is invalid"),
        ("type", "synchronous command handler"),
        ("async", "synchronous command handler"),
        ("command_type", "hook command is invalid"),
        ("command_content", "hook command is invalid"),
        ("windows_command", "hook command is invalid"),
        ("windows_call_operator", "PowerShell call operator"),
        ("matcher", "must match every tool"),
    ],
)
def test_codex_marketplace_smoke_rejects_invalid_handler_schema(
    tmp_path: Path,
    corruption: str,
    message: str,
    private_installer_launcher,
) -> None:
    _home, manifest = _marketplace_bundle(tmp_path / corruption)
    path = manifest.parents[1] / "hooks" / "hooks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    hook_map = payload["hooks"]
    registration = hook_map["UserPromptSubmit"][0]
    handler = registration["hooks"][0]
    if corruption == "extra_event":
        hook_map["Extra"] = hook_map["Stop"]
    elif corruption == "registration":
        hook_map["UserPromptSubmit"] = {}
    elif corruption == "handler":
        registration["hooks"] = []
    elif corruption == "timeout_sec":
        handler["timeoutSec"] = handler.pop("timeout")
    elif corruption == "timeout_bool":
        handler["timeout"] = True
    elif corruption == "timeout_text":
        handler["timeout"] = "30"
    elif corruption == "timeout_zero":
        handler["timeout"] = 0
    elif corruption == "type":
        handler["type"] = "prompt"
    elif corruption == "async":
        handler["async"] = True
    elif corruption == "command_type":
        handler["command"] = 7
    elif corruption == "command_content":
        handler["command"] = "echo unsafe"
    elif corruption == "windows_command":
        handler["commandWindows"] = "echo unsafe"
    elif corruption == "windows_call_operator":
        handler["commandWindows"] = handler["commandWindows"].removeprefix("& ")
    elif corruption == "matcher":
        hook_map["PostToolUse"][0]["matcher"] = "Write"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        smoke._smoke_marketplace_bundle("codex", manifest)


def test_marketplace_smoke_rejects_skill_and_mcp_contracts(
    tmp_path: Path,
    private_installer_launcher,
) -> None:
    _home, manifest = _marketplace_bundle(tmp_path / "skill")
    skill = manifest.parents[1] / "skills" / "agency" / "SKILL.md"
    skill.write_text("incomplete", encoding="utf-8")
    with pytest.raises(RuntimeError, match="control skill"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "args")
    mcp = manifest.parents[1] / ".mcp.json"
    data = json.loads(mcp.read_text(encoding="utf-8"))
    data["mcpServers"]["agency-runtime"]["args"] = []
    mcp.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid Agency Runtime MCP"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "command")
    mcp = manifest.parents[1] / ".mcp.json"
    data = json.loads(mcp.read_text(encoding="utf-8"))
    data["mcpServers"]["agency-runtime"]["command"] = "python"
    mcp.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="absolute interpreter"):
        smoke._smoke_marketplace_bundle("codex", manifest)

    _home, manifest = _marketplace_bundle(tmp_path / "alternate-command")
    mcp = manifest.parents[1] / ".mcp.json"
    data = json.loads(mcp.read_text(encoding="utf-8"))
    data["mcpServers"]["agency-runtime"]["command"] = str((tmp_path / "other-python.exe").resolve())
    mcp.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="installed launcher identity"):
        smoke._smoke_marketplace_bundle("codex", manifest)


def test_generated_plugin_reports_install_and_import_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(smoke, "install_agent_adapter", lambda *_args, **_kwargs: {"ok": False})
    with pytest.raises(RuntimeError, match="False"):
        smoke._smoke_generated_plugin("hermes", tmp_path)

    plugin = tmp_path / "plugin.py"
    plugin.write_text("pass", encoding="utf-8")
    monkeypatch.setattr(
        smoke,
        "install_agent_adapter",
        lambda *_args, **_kwargs: {"ok": True, "plugin_path": str(plugin)},
    )
    monkeypatch.setattr(smoke.importlib.util, "spec_from_file_location", lambda *_args: None)
    with pytest.raises(RuntimeError, match="could not import"):
        smoke._smoke_generated_plugin("hermes", tmp_path)


@pytest.mark.parametrize("failure", ["hooks", "commands", "status"])
def test_generated_hermes_plugin_validates_runtime_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    plugin = tmp_path / "plugin.py"
    plugin.write_text("pass", encoding="utf-8")
    monkeypatch.setattr(
        smoke,
        "install_agent_adapter",
        lambda *_args, **_kwargs: {"ok": True, "plugin_path": str(plugin)},
    )

    module = SimpleNamespace()

    def register(ctx: Any) -> None:
        if failure != "hooks":
            for name in (
                "pre_llm_call",
                "post_tool_call",
                "post_api_request",
                "pre_verify",
                "transform_llm_output",
                "on_session_end",
            ):
                ctx.register_hook(name, lambda **_kwargs: None)
        if failure != "commands":
            result = "wrong" if failure == "status" else "Agency Runtime is enabled for hermes."
            ctx.register_command("agency", lambda _args: result)

    module.register = register
    module._get_adapter = lambda: SimpleNamespace()
    loader = SimpleNamespace(exec_module=lambda _module: None)
    monkeypatch.setattr(
        smoke.importlib.util,
        "spec_from_file_location",
        lambda *_args: SimpleNamespace(loader=loader),
    )
    monkeypatch.setattr(smoke.importlib.util, "module_from_spec", lambda _spec: module)
    message = {
        "hooks": "missing hooks",
        "commands": "control command",
        "status": "invalid response",
    }
    with pytest.raises(RuntimeError, match=message[failure]):
        smoke._smoke_generated_plugin("hermes", tmp_path)


def test_run_smoke_empty_hosts_and_failure_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke, "detect_installed_agents", lambda: [])
    monkeypatch.setattr(
        smoke,
        "run_delegation_eval",
        lambda: {"passed": False, "passed_count": 1, "failed_count": 2},
    )
    report = smoke.run_smoke()
    assert report["passed"] is False
    assert report["failed_count"] == 1
    assert report["skipped_count"] == 1
    assert (
        next(item for item in report["checks"] if item["name"] == "host_plugins")["status"]
        == "skip"
    )


def test_run_smoke_uses_active_roster_and_records_plugin_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Store:
        def __init__(self, _path: Path) -> None:
            pass

        def database_stats(self) -> dict[str, Any]:
            return {"ok": True}

        def get_enabled_roster(self) -> list[dict[str, str]]:
            return [{"slug": "active"}]

    monkeypatch.setattr(smoke, "Store", _Store)
    monkeypatch.setattr(smoke, "detect_installed_agents", lambda: ["hermes"])
    monkeypatch.setattr(
        smoke,
        "run_delegation_eval",
        lambda: {"passed": True, "passed_count": 3, "failed_count": 0},
    )
    monkeypatch.setattr(
        smoke,
        "_smoke_generated_plugin",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("broken plugin")),
    )
    report = smoke.run_smoke()
    roster = next(item for item in report["checks"] if item["name"] == "routing_roster_available")
    assert roster["detail"] == {"agent_count": 1, "source": "active"}
    assert report["failed_count"] == 1
