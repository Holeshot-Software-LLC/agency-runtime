"""Adapter parity and generated-plugin contracts for all host adapters."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.installer import install_agent_adapter
from agency_runtime.core.process_argv import absolute_executable_path
from agency_runtime.core.store.sqlite import Store

ADAPTERS = [HermesAdapter, OpenClawAdapter, CodexAdapter, ClaudeAdapter, GenericAdapter]


class FakeHookContext:
    def __init__(self) -> None:
        self.hooks: dict[str, Any] = {}
        self.commands: dict[str, Any] = {}

    def register_hook(self, name: str, fn: Any) -> None:
        self.hooks[name] = fn

    def register_command(self, name: str, fn: Any, **_kwargs: Any) -> None:
        self.commands[name] = fn


def test_explicit_host_home_rejects_path_escape(tmp_path: Path) -> None:
    from agency_runtime.core.installer import _host_path

    with pytest.raises(ValueError, match="escapes explicit home boundary"):
        _host_path("~/../outside", home_dir=tmp_path)


def _adapter(adapter_cls: type, store: Store):
    if adapter_cls is GenericAdapter:
        return adapter_cls(store=store, cli_cmd="definitely-not-installed")
    return adapter_cls(store=store)


def test_cli_adapter_availability_uses_path_lookup_without_shelling_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = Store(tmp_path / "agency.db")
    requested: list[str] = []

    def fake_which(name: str) -> str | None:
        requested.append(name)
        return f"/bin/{name}" if name in {"codex", "claude", "custom-agent"} else None

    def fail_run(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("is_available must not spawn subprocess.run")

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr(subprocess, "run", fail_run)

    assert CodexAdapter(store=store).is_available() is True
    assert ClaudeAdapter(store=store).is_available() is True
    assert GenericAdapter(store=store, cli_cmd="custom-agent").is_available() is True
    assert GenericAdapter(store=store, cli_cmd="missing-agent").is_available() is False
    assert requested == ["codex", "claude", "custom-agent", "missing-agent"]


@pytest.mark.parametrize("adapter_cls", ADAPTERS)
def test_all_adapters_report_tool_call_evidence_from_store(
    adapter_cls: type, tmp_path: Path
) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = _adapter(adapter_cls, store)

    adapter.post_tool_call_handler(
        tool_name="skill_view",
        args={"name": "agent-reach"},
        session_id="session-1",
    )
    adapter.post_tool_call_handler(
        tool_name="agency_agents_load",
        args={"agent": "software-architect"},
        session_id="session-1",
    )
    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"goal": "audit installer evidence"},
        session_id="session-1",
    )

    assert adapter.report_skills_loaded("session-1") == ["agent-reach"]
    assert adapter.report_specialists_loaded("session-1") == ["software-architect"]
    delegations = store.get_delegations_for_session("session-1")
    assert delegations[0]["host"] == adapter.host_name
    assert delegations[0]["backend"] == "delegate_task"
    assert delegations[0]["status"] == "delegated"


@pytest.mark.parametrize("adapter_cls", ADAPTERS)
def test_all_adapters_post_api_request_is_safe_and_records_when_model_present(
    adapter_cls: type, tmp_path: Path
) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = _adapter(adapter_cls, store)

    adapter.post_api_request_handler(
        response={"model": "test-provider/test-model"},
        model="task-general",
        model_group="task-general",
        session_id="session-1",
        trace_id="trace-1",
        resolved_provider="explicit-provider",
        api_base="https://models.example/v1",
        attempted_fallbacks=2,
        model_id="receipt-id-1",
        source="wrapper",
        status="failed",
    )

    receipt = store.get_model_receipt("trace-1")
    assert receipt is not None
    assert receipt["host"] == adapter.host_name
    assert receipt["requested_model"] == "task-general"
    assert receipt["model_group"] == "task-general"
    assert receipt["resolved_provider"] == "explicit-provider"
    assert receipt["resolved_model"] == "test-model"
    assert receipt["api_base"] == "https://models.example/v1"
    assert receipt["attempted_fallbacks"] == 2
    assert receipt["model_id"] == "receipt-id-1"
    assert receipt["source"] == "wrapper"
    assert receipt["status"] == "failed"


def test_generated_hermes_plugin_imports_and_registers_native_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "hermes.db"))
    (tmp_path / ".hermes" / "plugins").mkdir(parents=True)

    result = install_agent_adapter("hermes", home_dir=tmp_path)
    assert result["ok"] is True
    plugin_path = Path(result["plugin_path"])
    assert plugin_path.is_relative_to(tmp_path)
    assert (plugin_path.parent / "plugin.yaml").exists()

    spec = importlib.util.spec_from_file_location("agency_runtime_generated_hermes", plugin_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ctx = FakeHookContext()
    module.register(ctx)
    assert {"pre_llm_call", "post_tool_call", "post_api_request", "transform_llm_output"} <= set(
        ctx.hooks
    )
    assert set(ctx.commands) == {"agency"}
    assert "disabled" in ctx.commands["agency"]("off")
    assert "disabled" in ctx.commands["agency"]("status")
    assert "enabled" in ctx.commands["agency"]("on")
    adapter = module._get_adapter()
    assert adapter.__class__.__name__ == "HermesAdapter"
    assert adapter.host_name == "hermes"
    # Generated plugins must not crash if their host emits a post-API hook with no model telemetry.
    assert ctx.hooks["post_api_request"](response={}, model="task-general", session_id="s1") is None
    receipt = adapter.store.get_model_receipt_for_session("s1")
    assert receipt is not None
    assert receipt["resolved_model"] == "unavailable"


@pytest.mark.parametrize(
    ("host", "manifest_dir"), [("codex", ".codex-plugin"), ("claude", ".claude-plugin")]
)
def test_generated_codex_and_claude_bundles_use_native_hooks_and_mcp(
    host: str,
    manifest_dir: str,
    tmp_path: Path,
) -> None:
    (tmp_path / f".{host}").mkdir()

    result = install_agent_adapter(host, home_dir=tmp_path)
    assert result["ok"] is True
    manifest_path = Path(result["plugin_path"])
    assert manifest_path.parent.name == manifest_dir
    plugin_root = manifest_path.parents[1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hooks = json.loads((plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    mcp = json.loads((plugin_root / ".mcp.json").read_text(encoding="utf-8"))
    skill = (plugin_root / "skills" / "agency" / "SKILL.md").read_text(encoding="utf-8")

    assert manifest["name"] == "agency-preflight"
    if host == "codex":
        assert manifest["hooks"] == "./hooks/hooks.json"
        assert manifest["interface"]["defaultPrompt"]
    assert "UserPromptSubmit" in hooks["hooks"]
    assert mcp["mcpServers"]["agency-runtime"]["args"] == [
        "-m",
        "agency_runtime.server.mcp",
        "--stdio",
    ]
    assert f"`ENABLE {host}`" in skill
    assert f"`DISABLE {host}`" in skill
    assert "`agency.host_status`" in skill
    assert "`agency.host_control`" in skill
    assert result["maturity"] == "staged-not-registered"


def test_openclaw_bridge_routes_user_prompts_but_ignores_revision_instructions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "bridge.db"))
    from agency_runtime.adapters.openclaw.node_bridge import handle
    from agency_runtime.core.policy.defaults import STARTER_ROSTER
    from agency_runtime.core.store.sqlite import Store

    store = Store(tmp_path / "bridge.db")
    for agent in STARTER_ROSTER:
        store.activate_agent(dict(agent))
    store.activate_agent({"slug": "agents-orchestrator", "name": "Agents Orchestrator"})
    store.activate_agent({"slug": "chief-of-staff", "name": "Chief of Staff"})

    routed = handle(
        {
            "action": "preflight",
            "sessionId": "bridge",
            "traceId": "bridge-trivial",
            "userMessage": "ping",
            "model": "task-general",
        }
    )
    correlated = handle(
        {
            "action": "preflight",
            "sessionId": "bridge",
            "traceId": "bridge-turn",
            "userMessage": "Review the authentication architecture and deployment controls.",
            "model": "task-general",
        }
    )
    skipped = handle(
        {
            "action": "preflight",
            "sessionId": "bridge",
            "userMessage": "Please revise. AGENCY HEADER INVALID: loaded none",
            "model": "task-general",
        }
    )
    recorded = handle(
        {
            "action": "post_tool_call",
            "sessionId": "bridge",
            "toolName": "agency_agents_load",
            "toolInput": {"agent": "chief-of-staff"},
            "toolResult": {"ok": True},
        }
    )
    verified = handle(
        {
            "action": "pre_verify",
            "sessionId": "bridge",
            "traceId": "bridge-turn",
            "finalResponse": "Draft without a header.",
            "model": "task-general",
        }
    )
    disabled = handle({"action": "control", "command": "off"})
    status = handle({"action": "control", "command": "status"})
    enabled = handle({"action": "control", "command": "on"})
    enabled_status = handle({"action": "control", "command": "status"})

    assert "agents-orchestrator, chief-of-staff" in routed["context"]
    assert correlated["context"]
    assert skipped == {}
    assert recorded == {}
    assert verified["action"] == "continue"
    activity = store.recent_runtime_activity(limit=20)
    assert activity["routing"][0]["trace_id"] == "bridge-turn"
    assert activity["finalizations"][0]["trace_id"] == "bridge-turn"
    assert disabled["runtime_enabled"] is False
    assert status["runtime_enabled"] is False
    assert enabled["runtime_enabled"] is True
    assert enabled_status["runtime_enabled"] is True
    assert "chief-of-staff" in store.get_specialists_for_session("bridge")


def test_generated_openclaw_plugin_is_native_openclaw_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".openclaw").mkdir()

    result = install_agent_adapter("openclaw", home_dir=tmp_path)
    assert result["ok"] is True
    plugin_path = Path(result["plugin_path"])
    assert plugin_path.name == "index.js"
    assert (
        plugin_path.parent
        == tmp_path / ".agency-runtime" / "host-plugins" / "openclaw" / "agency-preflight"
    )

    manifest = json.loads((plugin_path.parent / "openclaw.plugin.json").read_text(encoding="utf-8"))
    package = json.loads((plugin_path.parent / "package.json").read_text(encoding="utf-8"))
    code = plugin_path.read_text(encoding="utf-8")

    assert manifest["id"] == "agency-preflight"
    assert manifest["activation"]["onStartup"] is True
    assert package["openclaw"]["extensions"] == ["./index.js"]
    assert "before_prompt_build" in code
    assert "before_agent_finalize" in code
    assert "api.registerCommand" in code
    assert 'name: "agency"' in code
    assert 'action: "control"' in code
    assert "event?.prompt" in code
    assert "event?.lastAssistantMessage" in code
    assert "agency_runtime.adapters.openclaw.node_bridge" in code
    assert "execFile" in code
    assert "spawnSync" not in code
    assert json.dumps(absolute_executable_path(sys.executable)) in code
