"""AR-367: a fail-open turn claims and acknowledges its resident binding.

Measured 2026-09-02 on the live claude host: a session whose turns failed
open (the AR-353 window) kept a binding row stuck ``pending`` or never got one
at all, so every later turn planned ``injected`` again and re-delivered the
whole kernel. The ready commit was the only place a planned binding was
claimed, and the Stop path only acknowledged bindings it could read from a
ready recipe. These tests pin the repaired lifecycle end to end on the
persistent host: claim on the fail-open close, projection in the completion
snapshot, acknowledgement at Stop, and ``reused`` delivery on the next turn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.fail_open_disclosure import FAIL_OPEN_DISCLOSURE_MARKER
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL
from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.store import resident_binding as resident_binding_store
from agency_runtime.core.store.sqlite import Store

SUBSTANTIVE_REQUEST = (
    "Investigate this unusual request thoroughly and produce a durable implementation."
)


@pytest.fixture(autouse=True)
def _stable_materialized_master_control(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = RuntimeControlSnapshot(
        schema_version=1,
        enabled=True,
        generation=0,
        updated_at="2026-07-17T00:00:00Z",
        source="test",
        materialized=True,
    )
    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        lambda **_kwargs: snapshot,
    )


def _persistent_store(path: Path) -> Store:
    store = Store(path)
    store.set_host_control("claude", enabled=False, expected_generation=0, source="test")
    store.set_host_control("claude", enabled=True, expected_generation=1, source="test")
    return store


def _binding_row(store: Store, session_id: str) -> dict[str, object] | None:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT delivery_state, pending_delivery_mode, pending_trace_id, last_trace_id "
            "FROM resident_manager_bindings WHERE session_id = ? AND host = 'claude'",
            (session_id,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        conn.close()


def _prompt(bridge: HookBridge, *, session_id: str, turn_id: str) -> str:
    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": turn_id,
            "prompt": SUBSTANTIVE_REQUEST,
        }
    )
    return str(result["hookSpecificOutput"]["additionalContext"])


def _stop(bridge: HookBridge, *, session_id: str, turn_id: str) -> dict[str, object]:
    return bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "turn_id": turn_id,
            "last_assistant_message": "Here is the answer, unstaffed.",
        }
    )


def test_fail_open_close_claims_the_planned_binding(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "claim.db")
    bridge = HookBridge("claude", store=store)

    context = _prompt(bridge, session_id="session", turn_id="turn-one")

    run = store.get_run("turn-one")
    assert run is not None and run["status"] == "preflight_failed"
    assert context.startswith(RESIDENT_MANAGER_KERNEL)
    assert FAIL_OPEN_DISCLOSURE_MARKER in context
    row = _binding_row(store, "session")
    assert row == {
        "delivery_state": "pending",
        "pending_delivery_mode": "injected",
        "pending_trace_id": "turn-one",
        "last_trace_id": "turn-one",
    }
    projected = store.pending_resident_manager_binding(
        session_id="session", host="claude", trace_id="turn-one"
    )
    assert projected is not None
    assert projected["delivery_mode"] == "injected"
    assert projected["host_mode"] == "persistent"
    assert (
        store.pending_resident_manager_binding(
            session_id="session", host="claude", trace_id="turn-other"
        )
        is None
    )


def test_completion_snapshot_projects_the_claimed_binding_for_a_fail_open_run(
    tmp_path: Path,
) -> None:
    store = _persistent_store(tmp_path / "snapshot.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")

    snapshot = store.get_completion_evidence_snapshot("session", "turn-one")

    binding = snapshot["resident_manager_binding"]
    assert binding is not None
    assert binding["delivery_mode"] == "injected"
    assert binding["host"] == "claude"
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="turn-one", binding=binding
    )
    assert _binding_row(store, "session")["delivery_state"] == "acknowledged"


def test_stop_acknowledges_the_fail_open_delivery_and_the_next_turn_reuses_it(
    tmp_path: Path,
) -> None:
    store = _persistent_store(tmp_path / "lifecycle.db")
    bridge = HookBridge("claude", store=store)

    first = _prompt(bridge, session_id="session", turn_id="turn-one")
    assert "delivery=injected" in first
    # Rule 8: the fail-open reply publishes, and the pass-through acknowledges
    # the kernel the capsule delivered.
    assert _stop(bridge, session_id="session", turn_id="turn-one") == {}
    assert _binding_row(store, "session")["delivery_state"] == "acknowledged"

    second = _prompt(bridge, session_id="session", turn_id="turn-two")

    # The second turn also fails open offline, but the binding is reused: the
    # kernel body is not re-delivered and the binding line says so.
    assert "delivery=reused" in second
    assert RESIDENT_MANAGER_KERNEL not in second
    assert FAIL_OPEN_DISCLOSURE_MARKER in second
    assert store.get_run("turn-two")["status"] == "preflight_failed"
    row = _binding_row(store, "session")
    assert row["delivery_state"] == "acknowledged"
    assert row["last_trace_id"] == "turn-two"


def test_a_conflicting_claim_never_fails_the_fail_open_close(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "conflict.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    # Leave turn-one pending (no Stop) and start another turn: its claim
    # conflicts with the pending trace, the close still lands, and the row is
    # left exactly as it was.
    before = _binding_row(store, "session")

    context = _prompt(bridge, session_id="session", turn_id="turn-two")

    assert store.get_run("turn-two")["status"] == "preflight_failed"
    assert FAIL_OPEN_DISCLOSURE_MARKER in context
    assert _binding_row(store, "session") == before
