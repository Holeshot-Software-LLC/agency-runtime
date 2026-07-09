"""Adapter parity and generated-plugin contracts for all host adapters."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.installer import install_agent_adapter
from agency_runtime.core.store.sqlite import Store


ADAPTERS = [HermesAdapter, OpenClawAdapter, CodexAdapter, ClaudeAdapter, GenericAdapter]


class FakeHookContext:
    def __init__(self) -> None:
        self.hooks: dict[str, Any] = {}

    def register_hook(self, name: str, fn: Any) -> None:
        self.hooks[name] = fn


def _adapter(adapter_cls: type, store: Store):
    if adapter_cls is GenericAdapter:
        return adapter_cls(store=store, cli_cmd="definitely-not-installed")
    return adapter_cls(store=store)


@pytest.mark.parametrize("adapter_cls", ADAPTERS)
def test_all_adapters_report_tool_call_evidence_from_store(adapter_cls: type, tmp_path: Path) -> None:
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
def test_all_adapters_post_api_request_is_safe_and_records_when_model_present(adapter_cls: type, tmp_path: Path) -> None:
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


@pytest.mark.parametrize(
    ("host", "expected_class", "expected_host"),
    [
        ("hermes", "HermesAdapter", "hermes"),
        ("openclaw", "OpenClawAdapter", "openclaw"),
        ("codex", "CodexAdapter", "codex"),
        ("claude", "ClaudeAdapter", "claude"),
    ],
)
def test_generated_plugins_import_and_register_host_specific_adapters(
    host: str,
    expected_class: str,
    expected_host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # Satisfy installer host detection without touching the real machine.
    if host == "hermes":
        (tmp_path / ".hermes-nexus" / "plugins").mkdir(parents=True)
    elif host == "openclaw":
        (tmp_path / ".openclaw").mkdir()
    elif host == "codex":
        (tmp_path / ".codex").mkdir()
    elif host == "claude":
        (tmp_path / ".claude").mkdir()

    result = install_agent_adapter(host)
    assert result["ok"] is True
    plugin_path = Path(result["plugin_path"])

    spec = importlib.util.spec_from_file_location(f"agency_runtime_generated_{host}", plugin_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ctx = FakeHookContext()
    module.register(ctx)
    assert {"pre_llm_call", "pre_verify", "post_tool_call", "post_api_request", "transform_llm_output"} <= set(ctx.hooks)
    adapter = module._get_adapter()
    assert adapter.__class__.__name__ == expected_class
    assert adapter.host_name == expected_host
    # OpenClaw/Codex/Claude generated plugins must not crash if their host emits
    # a post-API hook with no model telemetry.
    assert ctx.hooks["post_api_request"](response={}, model="task-general", session_id="s1") is None
    receipt = adapter.store.get_model_receipt_for_session("s1")
    assert receipt is not None
    assert receipt["resolved_model"] == "unavailable"
