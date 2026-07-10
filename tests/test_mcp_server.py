"""Tests for the Agency Runtime MCP facade."""

from __future__ import annotations

from pathlib import Path

from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import MCP_TOOLS, handle_tool_call


def _seed_store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "agency.db")
    store.activate_agent({
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "division": "engineering",
        "description": "Reviews code quality and security.",
        "source": "test",
        "version": "1.0",
        "hash": "abc123",
        "categories": ["code-review"],
        "capabilities": ["code-review"],
        "tool_affinity": [],
        "prompt_path": "",
    })
    return store


def test_mcp_exposes_explain_selection_tool() -> None:
    names = {tool["name"] for tool in MCP_TOOLS}

    assert "agency.explain_selection" in names


def test_mcp_explain_selection_returns_receipt(tmp_path: Path) -> None:
    from agency_runtime.core.selector.cache import clear_cache
    from agency_runtime.core.selector.stickiness import clear_session_routing

    clear_cache()
    clear_session_routing()
    store = _seed_store(tmp_path)

    receipt = handle_tool_call(
        "agency.explain_selection",
        {"session_id": "s1", "task": "review code quality", "limit": 5},
        store=store,
    )

    assert receipt["schema_version"] == "agency.selection_explain.v1"
    assert receipt["selected"][0]["slug"] == "code-reviewer"
    assert receipt["signals"]["selection"]["roster_size"] == 1
