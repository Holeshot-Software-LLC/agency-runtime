"""Just-in-time staffing must behave identically on every hook-model host.

Host parity is the product claim, not a trade-off: a child the host spawned on its
own initiative gets a specialist on codex, claude and zcode alike.  These tests
exist because the capability was previously proven only on claude, which left the
other two hosts free to regress silently while still looking covered.

openclaw and hermes are deliberately absent.  ``HookBridge`` cannot be constructed
for them at all -- they have no PreToolUse-equivalent interception point where a
child's launch input can still be rewritten -- so parity for those hosts is an
adapter-protocol question, not a hook-gating one.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

import pytest

from agency_runtime.adapters.hooks import _JIT_STAFFING_MAX_CARDS as JIT_STAFFING_MAX_CARDS
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.native_child_prompt_delivery import (
    parse_all_jit_specialist_deliveries,
    parse_jit_specialist_delivery,
    parse_native_child_prompt_delivery,
)

# Each hook-model host, with the exact spawn tool and task field it actually uses.
_HOSTS = (
    pytest.param("claude", "Agent", "prompt", id="claude"),
    pytest.param("zcode", "Agent", "prompt", id="zcode"),
    pytest.param("codex", "functions.collaboration.spawn_agent", "message", id="codex"),
)

_TASK = "Speed up the slow SQL query and add an index."


class _JitRosterStore:
    """Only what just-in-time staffing reads: an open trace and a versioned roster."""

    def __init__(self) -> None:
        self.prompt = "You are the exact database tuning specialist for slow SQL queries."
        self.hash = sha256(self.prompt.encode()).hexdigest()
        self.loaded: list[tuple[str, str, str]] = []

    def get_open_traces_for_session(self, _session_id: str) -> list[str]:
        return ["trace"]

    def get_run(self, trace_id: str) -> dict[str, Any] | None:
        # Only the real routed turn exists; a tool identity must not resolve to a run.
        if trace_id != "trace":
            return None
        return {"session_id": "session", "trace_id": "trace", "status": "active"}

    def get_completion_evidence_snapshot(self, session_id: str, trace_id: str) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "status": "active",
            "delivery_mode": "direct",
            "selected_specialists": [],
            "unit_agent_plan": [],
        }

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "slug": "database-optimizer",
                "agent_slug": "database-optimizer",
                "version": "v1",
                "hash": self.hash,
                "description": "Tunes slow SQL queries, indexes, and query plans",
                "capabilities": ["sql", "index", "query", "database"],
            }
        ]

    def get_versioned_specialist_prompt(
        self,
        slug: str,
        version: str,
        content_hash: str,
        *,
        max_chars: int,
    ) -> dict[str, Any] | None:
        if slug != "database-optimizer" or version != "v1" or content_hash != self.hash:
            return None
        return {
            "slug": slug,
            "version": version,
            "hash": content_hash,
            "prompt_body": self.prompt[:max_chars],
            "prompt_truncated": len(self.prompt) > max_chars,
        }

    def record_specialist_loaded(
        self,
        session_id: str,
        agent_slug: str,
        *,
        trace_id: str = "",
    ) -> None:
        self.loaded.append((session_id, agent_slug, trace_id))


def _unplanned_child_payload(tool_name: str, task_field: str, task: str) -> dict[str, Any]:
    # No planned native label means no plan row can match, which is exactly how a
    # child the host spawned on its own initiative arrives.
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "session",
        "tool_use_id": "tool-1",
        "tool_name": tool_name,
        "tool_input": {task_field: task},
    }


@pytest.mark.parametrize(("host", "tool_name", "task_field"), _HOSTS)
def test_host_initiated_child_is_staffed_just_in_time_on_every_host(
    host: str,
    tool_name: str,
    task_field: str,
) -> None:
    store = _JitRosterStore()

    result = HookBridge(host, store=store).handle(
        _unplanned_child_payload(tool_name, task_field, _TASK)
    )

    delivered = result["hookSpecificOutput"]["updatedInput"][task_field]
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "[AGENCY JIT SPECIALIST v5]" in delivered
    assert store.prompt in delivered
    # Staffed but not accounted: no grant is issued, so the parent's turn gains no
    # delegation obligation it would then have to finalize against.
    assert "activation_token" not in delivered
    assert parse_native_child_prompt_delivery(delivered) is None
    delivery = parse_jit_specialist_delivery(delivered)
    assert delivery is not None
    assert delivery.host == host
    assert delivery.specialist_slug == "database-optimizer"
    assert delivery.specialist_version == "v1"
    assert delivery.original_task == _TASK
    # The audit row carries the parent trace, never the tool identity.
    assert store.loaded == [("session", "database-optimizer", "trace")]


@pytest.mark.parametrize(("host", "tool_name", "task_field"), _HOSTS)
def test_host_initiated_child_runs_unstaffed_when_no_specialist_fits_on_every_host(
    host: str,
    tool_name: str,
    task_field: str,
) -> None:
    class _EmptyRoster(_JitRosterStore):
        def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
            return []

    store = _EmptyRoster()

    result = HookBridge(host, store=store).handle(
        _unplanned_child_payload(tool_name, task_field, _TASK)
    )

    # Abstaining must never block the child the host chose to spawn.
    assert result == {}
    assert store.loaded == []


@pytest.mark.parametrize(("host", "tool_name", "task_field"), _HOSTS)
def test_just_in_time_staffing_is_never_reapplied_on_every_host(
    host: str,
    tool_name: str,
    task_field: str,
) -> None:
    store = _JitRosterStore()
    bridge = HookBridge(host, store=store)

    delivered = bridge.handle(_unplanned_child_payload(tool_name, task_field, _TASK))[
        "hookSpecificOutput"
    ]["updatedInput"][task_field]
    again = bridge.handle(_unplanned_child_payload(tool_name, task_field, delivered))

    assert again == {}
    assert store.loaded == [("session", "database-optimizer", "trace")]


def test_opaque_codex_child_runs_unstaffed_rather_than_blocked() -> None:
    """An encrypted Codex spawn message has no rewritable surface.

    This is the one irreducible parity gap: Agency cannot append a specialist to
    ciphertext it cannot read.  The required behaviour is therefore fail-open --
    the child runs exactly as it otherwise would, with no specialist and no denial.
    """

    store = _JitRosterStore()

    result = HookBridge("codex", store=store).handle(
        _unplanned_child_payload(
            "functions.collaboration.spawn_agent",
            "message",
            "gAAAAA" + "a" * 40,
        )
    )

    assert result == {}
    assert store.loaded == []


def test_openclaw_and_hermes_have_no_hook_model_to_staff_through() -> None:
    """Pin the reason those hosts are absent above, so the gap stays visible.

    If either host ever gains a PreToolUse-equivalent, this test fails and forces
    the parity question to be answered deliberately rather than by omission.
    """

    for host in ("openclaw", "hermes"):
        with pytest.raises(ValueError, match="unsupported hook host"):
            HookBridge(host, store=_JitRosterStore())


class _PluralRosterStore(_JitRosterStore):
    """Three specialists that all fit one multi-part assignment."""

    def __init__(self) -> None:
        super().__init__()
        self.bodies = {
            "database-optimizer": self.prompt,
            "backend-architect": "You are the exact backend API design specialist.",
            "test-writer": "You are the exact automated test authoring specialist.",
        }
        self.hashes = {
            slug: sha256(body.encode()).hexdigest() for slug, body in self.bodies.items()
        }

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "slug": "database-optimizer",
                "agent_slug": "database-optimizer",
                "version": "v1",
                "hash": self.hashes["database-optimizer"],
                "description": "Tunes slow SQL queries, indexes, and query plans",
                "capabilities": ["sql", "index", "query", "database"],
            },
            {
                "slug": "backend-architect",
                "agent_slug": "backend-architect",
                "version": "v1",
                "hash": self.hashes["backend-architect"],
                "description": "Designs backend API endpoints and service boundaries",
                "capabilities": ["api", "endpoint", "backend", "query"],
            },
            {
                "slug": "test-writer",
                "agent_slug": "test-writer",
                "version": "v1",
                "hash": self.hashes["test-writer"],
                "description": "Writes automated tests for new endpoints and queries",
                "capabilities": ["test", "endpoint", "query", "index"],
            },
        ]

    def get_versioned_specialist_prompt(
        self,
        slug: str,
        version: str,
        content_hash: str,
        *,
        max_chars: int,
    ) -> dict[str, Any] | None:
        body = self.bodies.get(slug)
        if body is None or version != "v1" or content_hash != self.hashes[slug]:
            return None
        return {
            "slug": slug,
            "version": version,
            "hash": content_hash,
            "prompt_body": body[:max_chars],
            "prompt_truncated": len(body) > max_chars,
        }


_PLURAL_TASK = "Add an indexed query endpoint and cover it with tests."


@pytest.mark.parametrize(("host", "tool_name", "task_field"), _HOSTS)
def test_a_host_initiated_child_is_handed_cards_plural(
    host: str,
    tool_name: str,
    task_field: str,
) -> None:
    """Rule 4 says harness-spawned children get cards -- plural, not one."""

    store = _PluralRosterStore()

    result = HookBridge(host, store=store).handle(
        _unplanned_child_payload(tool_name, task_field, _PLURAL_TASK)
    )

    delivered = result["hookSpecificOutput"]["updatedInput"][task_field]
    deliveries = parse_all_jit_specialist_deliveries(delivered)
    assert len(deliveries) > 1, "a child that needs several specialists must get several"
    assert len(deliveries) <= JIT_STAFFING_MAX_CARDS
    # Every card is independently verifiable against its own pinned version.
    for delivery in deliveries:
        assert delivery.host == host
        assert delivery.prompt_body == store.bodies[delivery.specialist_slug]
        assert delivery.specialist_prompt_hash == store.hashes[delivery.specialist_slug]
    # The host's own task survives intact underneath every card.
    assert {delivery.original_task for delivery in deliveries} == {_PLURAL_TASK}


def test_every_delivered_card_is_recorded_as_loaded() -> None:
    """Staffed but not accounted still means each card is auditable."""

    store = _PluralRosterStore()

    result = HookBridge("claude", store=store).handle(
        _unplanned_child_payload("Agent", "prompt", _PLURAL_TASK)
    )

    delivered = result["hookSpecificOutput"]["updatedInput"]["prompt"]
    staffed = {d.specialist_slug for d in parse_all_jit_specialist_deliveries(delivered)}
    recorded = {slug for _session, slug, _trace in store.loaded}
    assert recorded == staffed
    assert all(trace == "trace" for _session, _slug, trace in store.loaded)


def test_plural_staffing_stays_idempotent() -> None:
    """Re-staffing an already multi-carded child must add nothing."""

    store = _PluralRosterStore()
    bridge = HookBridge("claude", store=store)

    delivered = bridge.handle(_unplanned_child_payload("Agent", "prompt", _PLURAL_TASK))[
        "hookSpecificOutput"
    ]["updatedInput"]["prompt"]
    first = list(store.loaded)
    again = bridge.handle(_unplanned_child_payload("Agent", "prompt", delivered))

    assert again == {}
    assert store.loaded == first


def test_a_child_whose_roster_offers_one_fit_still_gets_exactly_one() -> None:
    """Plural is a ceiling, not a quota: never pad a team to reach it."""

    store = _JitRosterStore()

    result = HookBridge("claude", store=store).handle(
        _unplanned_child_payload("Agent", "prompt", _TASK)
    )

    delivered = result["hookSpecificOutput"]["updatedInput"]["prompt"]
    assert len(parse_all_jit_specialist_deliveries(delivered)) == 1
