"""Rule 9 checked per capability instead of per verb.

Rule 9 says a capability that exists on one host and not another is incomplete,
not a trade-off. Parity is already tested *per host* — each generated plugin has
its own test asserting it registers the hooks it is supposed to. What nothing
asserted is that the five sets **cover the same boundaries**. Drop
``subagent_spawned`` from the OpenClaw plugin and rule 4 quietly stops holding on
that host while every existing test still passes.

The trap this replaces: `agency hook` accepts only codex, claude, and zcode, and
that looks like a parity gap until you notice Hermes and OpenClaw reach Agency
through ``adapters.hermes.bridge`` and ``adapters.openclaw.node_bridge``, because
that is what their plugin systems dictate. The verb differs; the coverage does
not. Asserting on event *names* would encode that same mistake, so this asserts
on boundaries and lets each host spell them however its harness spells them.

Two assertions, and the second is the one that bites:

1. Every host covers every required boundary.
2. Every event name claimed below is actually present in that host's shipped
   artifact — so the map cannot rot into a fiction that still passes.
"""

from __future__ import annotations

import re

import pytest

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_payloads import (
    claude_hooks,
    codex_hooks,
    hermes_plugin,
    openclaw_index,
    zcode_hooks,
)

_TIMEOUT_SECONDS = 30

HOSTS = ("codex", "claude", "zcode", "hermes", "openclaw")


def _shipped_events() -> dict[str, frozenset[str]]:
    """Read each host's event set out of the artifact the installer actually writes.

    Deriving these from the rendered payloads rather than from a constant is the
    point: a test that restates a list next to the list proves nothing.
    """

    openclaw_source = openclaw_index(_TIMEOUT_SECONDS)
    hermes_source = hermes_plugin(_TIMEOUT_SECONDS, AgencyConfig())
    openclaw_events = set(re.findall(r'api\.on\("([a-z_]+)"', openclaw_source))
    if "api.registerAgentToolResultMiddleware(" in openclaw_source:
        openclaw_events.add("agent_tool_result_middleware")
    return {
        "codex": frozenset(codex_hooks(_TIMEOUT_SECONDS)["hooks"]),
        "claude": frozenset(claude_hooks(_TIMEOUT_SECONDS)["hooks"]),
        "zcode": frozenset(zcode_hooks(_TIMEOUT_SECONDS)["hooks"]["events"]),
        "hermes": frozenset(re.findall(r'register_hook\("([a-z_]+)"', hermes_source)),
        "openclaw": frozenset(openclaw_events),
    }


# Each boundary names a moment the vision depends on, then lists the events that
# reach it on each host. A host satisfies a boundary if it ships ANY of them —
# harnesses disagree about vocabulary, not about when the moment happens.
REQUIRED_BOUNDARIES: dict[str, tuple[str, dict[str, tuple[str, ...]]]] = {
    "prompt_observed": (
        "Rule 1 — selection is inference-based, so something must see what was asked.",
        {
            "codex": ("UserPromptSubmit",),
            "claude": ("UserPromptSubmit",),
            "zcode": ("UserPromptSubmit",),
            "hermes": ("pre_llm_call",),
            "openclaw": ("before_prompt_build",),
        },
    ),
    "child_started": (
        "Rule 4 — a harness-spawned child must be handed a card, which requires "
        "observing that it started. ZCode has no SubagentStart: native children "
        "arrive through the Agent tool, so its PreToolUse is matched on 'Agent' "
        "and that IS its child-start boundary.",
        {
            "codex": ("SubagentStart",),
            "claude": ("SubagentStart",),
            "zcode": ("PreToolUse",),
            "hermes": ("subagent_start",),
            "openclaw": ("subagent_spawned",),
        },
    ),
    "child_finished": (
        "Rule 7 — a spawned child's lifetime IS its turn for card expiry, so the "
        "end of that lifetime has to be observable.",
        {
            "codex": ("SubagentStop",),
            "claude": ("SubagentStop",),
            "zcode": ("PostToolUse",),
            "hermes": ("subagent_stop",),
            "openclaw": ("subagent_ended",),
        },
    ),
    "tool_observed": (
        "Evidence — which skills and specialists a turn actually loaded is read "
        "off tool calls, and `evidence children` is the only proof of rule 4.",
        {
            "codex": ("PostToolUse",),
            "claude": ("PostToolUse",),
            "zcode": ("PostToolUse",),
            "hermes": ("post_tool_call",),
            "openclaw": ("agent_tool_result_middleware",),
        },
    ),
    "turn_finalized": (
        "Rule 8 — the verifier's definite negative and the malformed-Stop "
        "boundary are the two paths still allowed to withhold a turn. Neither "
        "exists without a finalize boundary to hang them on.",
        {
            "codex": ("Stop",),
            "claude": ("Stop",),
            "zcode": ("Stop",),
            "hermes": ("pre_verify", "transform_llm_output"),
            "openclaw": ("before_agent_finalize",),
        },
    ),
    "session_started": (
        "Rule 8 again, from the other side — Agency has to know a session began "
        "to get out of the way for the whole of it rather than per event.",
        {
            "codex": ("SessionStart",),
            "claude": ("SessionStart",),
            "zcode": ("SessionStart",),
            "hermes": ("pre_llm_call",),
            "openclaw": ("before_agent_run", "gateway_start"),
        },
    ),
}

# Deliberately NOT required, so the omissions are decisions rather than oversights:
#
#   PostCompact  — "never reinstate after compaction" is a real vision rule, but
#                  compaction is a Claude-family concept. Codex and Claude ship
#                  it, ZCode does not support it, and Hermes and OpenClaw have no
#                  equivalent moment. Requiring it would fail three hosts for not
#                  having a feature their harness does not have.
#   SessionEnd   — Claude and Hermes only. Turn-scoped expiry hangs off
#                  `turn_finalized`, not session teardown, so nothing in the
#                  vision needs this.
#   model receipt — Hermes (`post_api_request`) and OpenClaw (`model_call_ended`)
#                  have a dedicated event; Codex/Claude/ZCode carry model identity
#                  inside other payloads. Same information, no shared boundary to
#                  assert on.


@pytest.mark.parametrize("boundary", sorted(REQUIRED_BOUNDARIES))
def test_every_host_covers_every_required_boundary(boundary: str) -> None:
    shipped = _shipped_events()
    rationale, per_host = REQUIRED_BOUNDARIES[boundary]

    assert set(per_host) == set(HOSTS), (
        f"boundary {boundary!r} does not name all five hosts; rule 9 makes a host "
        f"missing from this map a gap, not an exemption"
    )

    uncovered = [host for host, events in per_host.items() if not (set(events) & shipped[host])]
    assert not uncovered, (
        f"{boundary!r} is not reachable on {', '.join(sorted(uncovered))}.\n{rationale}"
    )


@pytest.mark.parametrize("host", HOSTS)
def test_declared_boundary_events_are_actually_shipped(host: str) -> None:
    """Keep the map above honest about the artifacts it describes.

    Without this, renaming an event in a generated plugin leaves the boundary map
    claiming a coverage that no longer exists, and the parity assertion passes on
    a name nothing registers.
    """

    shipped = _shipped_events()[host]
    claimed = {
        event for _rationale, per_host in REQUIRED_BOUNDARIES.values() for event in per_host[host]
    }

    assert claimed <= shipped, (
        f"{host} boundary map names events its installed artifact does not "
        f"register: {sorted(claimed - shipped)}"
    )
