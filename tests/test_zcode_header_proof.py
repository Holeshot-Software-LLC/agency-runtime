"""Proof that a live ZCode turn receives the Agency header.

Drives the real HookBridge entry point a ZCode UserPromptSubmit hook calls,
with the true host=zcode identity. Before the WP11 fixes this path raised
``ValueError("isolated specialist delivery is unsupported for host: zcode")``;
these tests prove it now returns the Agency banner and a routed specialist team.
"""

from __future__ import annotations

from pathlib import Path

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.store.sqlite import Store


def test_zcode_adapter_carries_its_own_host_identity(tmp_path: Path) -> None:
    # The ZCode adapter must keep its own identity so runtime-control and
    # evidence are attributed to zcode, not masqueraded as claude.
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("zcode", store=store)

    assert bridge.host == "zcode"
    assert bridge.adapter.host_name == "zcode"


def test_zcode_usersubmit_emits_agency_header_and_routed_team(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("zcode", store=store)

    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "proof-session",
            "turn_id": "proof-turn",
            "prompt": "Review this authentication code for correctness and security.",
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]

    # The resident-manager kernel header is the visible Agency banner.
    assert "resident-manager kernel" in context, context[:300]
    assert "[AGENCY PREFLIGHT]" in context, context[:300]
    # The routing result named the correct specialists for the ask, proving the
    # isolated-delivery path (the one that raised before WP11) now completes.
    assert "code-reviewer" in context, context[:400]
    assert "ai-generated-code-security-auditor" in context, context[:400]
    # ZCode-correct native-delegation guidance (Agent tool, not spawn_agent).
    assert "`Agent`" in context, context[:600]
