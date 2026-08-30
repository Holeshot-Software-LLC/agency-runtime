"""Durable bind-once lifecycle tests for the compact resident-manager pair."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core import preflight as preflight_module
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.header.contract import (
    EvidenceCorrelationError,
    _validated_resident_binding,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.resident_manager_binding import build_resident_manager_binding
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL
from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.store import resident_binding as resident_binding_store
from agency_runtime.core.store.sqlite import Store


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
    store.set_host_control(
        "claude",
        enabled=False,
        expected_generation=0,
        source="test-materialize",
    )
    store.set_host_control(
        "claude",
        enabled=True,
        expected_generation=1,
        source="test-materialize",
    )
    return store


def _ack(store: Store, *, session_id: str, trace_id: str) -> bool:
    snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
    return store.acknowledge_resident_manager_binding(
        session_id=session_id,
        host="claude",
        trace_id=trace_id,
        binding=snapshot["resident_manager_binding"],
    )


def _commit_binding(
    store: Store,
    *,
    binding: object,
    trace_id: str,
    session_id: str = "session",
) -> bool:
    connection = store._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        committed = store._commit_resident_manager_binding(
            connection,
            session_id=session_id,
            trace_id=trace_id,
            binding=binding,
        )
        connection.commit() if committed else connection.rollback()
        return committed
    finally:
        connection.close()


def _prompt(bridge: HookBridge, *, session_id: str, turn_id: str) -> dict:
    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": turn_id,
            "prompt": "ping",
        }
    )
    return result["hookSpecificOutput"]


def test_persistent_host_injects_once_reuses_and_restores_after_compaction(
    tmp_path: Path,
) -> None:
    store = _persistent_store(tmp_path / "persistent.db")
    bridge = HookBridge("claude", store=store)

    first = _prompt(bridge, session_id="session", turn_id="turn-one")["additionalContext"]
    assert _ack(store, session_id="session", trace_id="turn-one")
    second = _prompt(bridge, session_id="session", turn_id="turn-two")["additionalContext"]

    assert first.startswith(RESIDENT_MANAGER_KERNEL)
    assert "delivery=injected" in first
    assert second.startswith("[Agency resident managers active")
    assert "delivery=reused" in second
    assert RESIDENT_MANAGER_KERNEL not in second
    assert _ack(store, session_id="session", trace_id="turn-two")

    assert bridge.handle({"hook_event_name": "PostCompact", "session_id": "session"}) == {}
    restored = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-three",
    )["additionalContext"]
    assert _ack(store, session_id="session", trace_id="turn-three")
    reused = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-four",
    )["additionalContext"]

    assert restored.startswith(RESIDENT_MANAGER_KERNEL)
    assert "delivery=restored" in restored
    assert reused.startswith("[Agency resident managers active")
    assert "delivery=reused" in reused
    assert RESIDENT_MANAGER_KERNEL not in reused

    snapshot = store.get_completion_evidence_snapshot("session", "turn-three")
    assert snapshot["resident_manager_binding"]["delivery_mode"] == "restored"
    assert snapshot["resident_manager_binding"]["kernel"] == snapshot["resident_manager_kernel"]


def test_compaction_signals_coalesce_into_one_restore(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "coalesce.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    assert _ack(store, session_id="session", trace_id="turn-one")

    assert bridge.handle({"hook_event_name": "PreCompact", "session_id": "session"}) == {}
    assert bridge.handle({"hook_event_name": "PostCompact", "session_id": "session"}) == {}
    assert bridge.handle({"hook_event_name": "PostCompact", "session_id": "session"}) == {}
    restored = _prompt(bridge, session_id="session", turn_id="turn-two")["additionalContext"]
    assert _ack(store, session_id="session", trace_id="turn-two")
    reused = _prompt(bridge, session_id="session", turn_id="turn-three")["additionalContext"]

    assert "delivery=restored" in restored
    assert "delivery=reused" in reused


def test_compaction_during_pending_restore_remains_outstanding_after_ack(
    tmp_path: Path,
) -> None:
    store = _persistent_store(tmp_path / "pending-restore.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    assert _ack(store, session_id="session", trace_id="turn-one")

    assert bridge.handle({"hook_event_name": "PostCompact", "session_id": "session"}) == {}
    first_restore = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-two",
    )["additionalContext"]
    assert "delivery=restored" in first_restore

    assert bridge.handle({"hook_event_name": "PostCompact", "session_id": "session"}) == {}
    assert _ack(store, session_id="session", trace_id="turn-two")
    second_restore = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-three",
    )["additionalContext"]
    assert "delivery=restored" in second_restore
    assert _ack(store, session_id="session", trace_id="turn-three")

    reused = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-four",
    )["additionalContext"]
    assert "delivery=reused" in reused


def test_precompact_alone_does_not_require_restore(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "precompact.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    assert _ack(store, session_id="session", trace_id="turn-one")

    assert bridge.handle({"hook_event_name": "PreCompact", "session_id": "session"}) == {}
    context = _prompt(
        bridge,
        session_id="session",
        turn_id="turn-two",
    )["additionalContext"]

    assert "delivery=reused" in context


def test_master_epoch_change_replaces_pending_binding_and_rejects_old_ack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation = {"value": 0}

    def master_snapshot(**_kwargs: object) -> RuntimeControlSnapshot:
        return RuntimeControlSnapshot(
            schema_version=1,
            enabled=True,
            generation=generation["value"],
            updated_at="2026-07-17T00:00:00Z",
            source="test",
            materialized=True,
        )

    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        master_snapshot,
    )
    store = _persistent_store(tmp_path / "master-epoch.db")
    first = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _commit_binding(store, binding=first, trace_id="turn-one")

    generation["value"] = 2
    replacement = store.plan_resident_manager_binding(
        session_id="session",
        host="claude",
    )
    assert replacement.delivery_mode == "injected"
    assert replacement.binding_id != first.binding_id
    assert _commit_binding(store, binding=replacement, trace_id="turn-two")
    assert not store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-one",
        binding=first,
    )
    assert store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-two",
        binding=replacement,
    )


def test_host_off_on_epoch_forces_fresh_binding(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "host-epoch.db")
    first = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _commit_binding(store, binding=first, trace_id="turn-one")
    assert store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-one",
        binding=first,
    )

    store.set_host_control(
        "claude",
        enabled=False,
        expected_generation=2,
        source="test-toggle",
    )
    store.set_host_control(
        "claude",
        enabled=True,
        expected_generation=3,
        source="test-toggle",
    )
    replacement = store.plan_resident_manager_binding(
        session_id="session",
        host="claude",
    )

    assert replacement.delivery_mode == "injected"
    assert replacement.binding_id != first.binding_id
    assert _commit_binding(store, binding=replacement, trace_id="turn-two")


def test_deleted_generation_zero_host_control_cannot_resurrect_old_binding(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "deleted-host-control.db")
    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO host_controls (host, enabled, generation, updated_at, source) "
            "VALUES ('claude', 1, 0, '2026-07-17T00:00:00Z', 'install')"
        )
        connection.commit()
    finally:
        connection.close()
    original = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _commit_binding(store, binding=original, trace_id="turn-one")
    assert store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-one",
        binding=original,
    )

    connection = store._connect()
    try:
        connection.execute("DELETE FROM host_controls WHERE host = 'claude'")
        connection.commit()
    finally:
        connection.close()
    ephemeral = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert ephemeral.control_epoch.host_materialized is False
    assert _commit_binding(store, binding=ephemeral, trace_id="turn-two")

    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO host_controls (host, enabled, generation, updated_at, source) "
            "VALUES ('claude', 1, 0, '2026-07-17T00:01:00Z', 'reinstall')"
        )
        connection.commit()
    finally:
        connection.close()
    replacement = store.plan_resident_manager_binding(
        session_id="session",
        host="claude",
    )

    assert replacement.binding_id == original.binding_id
    assert replacement.delivery_mode == "injected"


def test_unmaterialized_epoch_is_noncacheable_and_deletes_stale_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"materialized": True}

    def master_snapshot(**_kwargs: object) -> RuntimeControlSnapshot:
        return RuntimeControlSnapshot(
            schema_version=1,
            enabled=True,
            generation=0,
            updated_at="2026-07-17T00:00:00Z",
            source="test" if state["materialized"] else "default",
            materialized=state["materialized"],
        )

    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        master_snapshot,
    )
    store = _persistent_store(tmp_path / "unmaterialized.db")
    durable = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _commit_binding(store, binding=durable, trace_id="turn-one")
    assert store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-one",
        binding=durable,
    )

    state["materialized"] = False
    ephemeral = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert ephemeral.delivery_mode == "injected"
    assert ephemeral.control_epoch.reusable is False
    assert _commit_binding(store, binding=ephemeral, trace_id="turn-two")
    connection = store._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM resident_manager_bindings").fetchone()[0] == 0
        )
    finally:
        connection.close()

    state["materialized"] = True
    same_generation = store.plan_resident_manager_binding(
        session_id="session",
        host="claude",
    )
    assert same_generation.delivery_mode == "injected"
    assert same_generation.binding_id == durable.binding_id


def test_restore_generation_overflow_fails_before_sql_arithmetic(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "restore-overflow.db")
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _commit_binding(store, binding=binding, trace_id="turn-one")
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE resident_manager_bindings SET restore_generation = ?",
            (2**63 - 1,),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="generation is exhausted"):
        store.mark_resident_manager_restore_required(
            session_id="session",
            host="claude",
        )


def test_hundred_turn_persistent_lifecycle_remains_bounded_across_compactions(
    tmp_path: Path,
) -> None:
    store = _persistent_store(tmp_path / "hundred-turns.db")

    for number in range(1, 101):
        compacted = number > 1 and number % 10 == 0
        if compacted:
            assert store.mark_resident_manager_restore_required(
                session_id="session",
                host="claude",
            )
        binding = store.plan_resident_manager_binding(
            session_id="session",
            host="claude",
        )
        expected_mode = "injected" if number == 1 else "restored" if compacted else "reused"
        assert binding.delivery_mode == expected_mode
        trace_id = f"turn-{number}"
        assert _commit_binding(store, binding=binding, trace_id=trace_id)
        assert store.acknowledge_resident_manager_binding(
            session_id="session",
            host="claude",
            trace_id=trace_id,
            binding=binding,
        )

    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT COUNT(*) AS count, restore_generation, applied_restore_generation "
            "FROM resident_manager_bindings"
        ).fetchone()
    finally:
        connection.close()
    assert row["count"] == 1
    assert row["restore_generation"] == row["applied_restore_generation"] == 10


@pytest.mark.parametrize(
    "host",
    ["codex", "openclaw", "hermes", "litellm", "unknown", "unrecognized-host"],
)
def test_request_scoped_hosts_never_persist_a_binding(tmp_path: Path, host: str) -> None:
    store = Store(tmp_path / f"{host}.db")
    first = store.plan_resident_manager_binding(session_id="session", host=host)
    second = store.plan_resident_manager_binding(session_id="session", host=host)

    assert first.delivery_mode == second.delivery_mode == "request"
    assert first.requires_kernel_injection is True
    connection = store._connect()
    try:
        assert store._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn-one",
            binding=first,
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM resident_manager_bindings").fetchone()[0] == 0
        )
    finally:
        connection.close()


def test_first_persistent_binding_claim_is_atomic(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "atomic.db")
    first = store.plan_resident_manager_binding(session_id="session", host="claude")
    competing = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert first.delivery_mode == competing.delivery_mode == "injected"

    connection = store._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        assert store._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn-one",
            binding=first,
        )
        connection.commit()

        connection.execute("BEGIN IMMEDIATE")
        assert not store._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn-two",
            binding=competing,
        )
        connection.rollback()
    finally:
        connection.close()

    assert store.acknowledge_resident_manager_binding(
        session_id="session",
        host="claude",
        trace_id="turn-one",
        binding=first,
    )
    reused = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert reused.delivery_mode == "reused"


def test_only_authoritative_compaction_completion_requires_restore(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "session-start.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    assert _ack(store, session_id="session", trace_id="turn-one")

    assert bridge.handle({"hook_event_name": "SessionStart", "session_id": "session"}) == {}
    reused = _prompt(bridge, session_id="session", turn_id="turn-two")["additionalContext"]
    assert "delivery=reused" in reused
    assert _ack(store, session_id="session", trace_id="turn-two")

    assert (
        bridge.handle(
            {
                "hook_event_name": "SessionStart",
                "session_id": "session",
                "source": "compact",
            }
        )
        == {}
    )
    restored = _prompt(bridge, session_id="session", turn_id="turn-three")["additionalContext"]
    assert "delivery=restored" in restored


def test_stale_kernel_binding_requires_fresh_injection(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "stale.db")
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    connection = store._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        assert store._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="turn-one",
            binding=binding,
        )
        connection.execute(
            "UPDATE resident_manager_bindings SET kernel_hash = ?",
            ("0" * 64,),
        )
        connection.commit()
    finally:
        connection.close()

    replacement = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert replacement.delivery_mode == "injected"


def test_session_end_retires_persistent_binding(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "session-end.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")

    assert bridge.handle({"hook_event_name": "SessionEnd", "session_id": "session"}) == {}
    replacement = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert replacement == build_resident_manager_binding(
        session_id="session",
        host="claude",
        delivery_mode="injected",
        control_epoch=replacement.control_epoch,
    )


def test_stop_acknowledges_a_pending_persistent_delivery(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "stop-ack.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")

    blocked = bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session",
            "turn_id": "turn-one",
            "last_assistant_message": "Draft without an Agency header.",
        }
    )

    assert blocked["decision"] == "block"
    assert (
        store.plan_resident_manager_binding(
            session_id="session",
            host="claude",
        ).delivery_mode
        == "reused"
    )


def test_stop_fails_closed_when_persistent_delivery_cannot_be_acknowledged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _persistent_store(tmp_path / "stop-ack-failure.db")
    bridge = HookBridge("claude", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    monkeypatch.setattr(
        store,
        "acknowledge_resident_manager_binding",
        lambda **_kwargs: False,
    )

    blocked = bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session",
            "turn_id": "turn-one",
            "last_assistant_message": "Draft.",
        }
    )

    assert blocked["continue"] is False
    assert "could not verify or persist" in blocked["stopReason"]


def test_ready_replay_fails_after_compaction_invalidates_its_binding(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "replay-restore.db")
    run_preflight(
        store,
        session_id="session",
        trace_id="turn-one",
        host="claude",
        user_message="ping",
    )
    assert _ack(store, session_id="session", trace_id="turn-one")
    assert store.mark_resident_manager_restore_required(
        session_id="session",
        host="claude",
    )

    with pytest.raises(RuntimeError, match="no longer replayable"):
        run_preflight(
            store,
            session_id="session",
            trace_id="turn-one",
            host="claude",
            user_message="ping",
        )


def test_ready_replay_fails_after_control_epoch_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation = {"value": 0}

    def master_snapshot(**_kwargs: object) -> RuntimeControlSnapshot:
        return RuntimeControlSnapshot(
            schema_version=1,
            enabled=True,
            generation=generation["value"],
            updated_at="2026-07-17T00:00:00Z",
            source="test",
            materialized=True,
        )

    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        master_snapshot,
    )
    store = _persistent_store(tmp_path / "replay-epoch.db")
    run_preflight(
        store,
        session_id="session",
        trace_id="turn-one",
        host="claude",
        user_message="ping",
    )
    assert _ack(store, session_id="session", trace_id="turn-one")

    generation["value"] = 2
    with pytest.raises(RuntimeError, match="no longer replayable"):
        run_preflight(
            store,
            session_id="session",
            trace_id="turn-one",
            host="claude",
            user_message="ping",
        )


def test_ready_snapshot_rejects_a_corrupted_recipe_version(tmp_path: Path) -> None:
    store = Store(tmp_path / "corrupt-ready.db")
    bridge = HookBridge("codex", store=store)
    _prompt(bridge, session_id="session", turn_id="turn-one")
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT preflight_result FROM runs WHERE trace_id = 'turn-one'"
        ).fetchone()
        recipe = json.loads(str(row["preflight_result"]))
        recipe["recipe_version"] = 999
        connection.execute(
            "UPDATE runs SET preflight_result = ? WHERE trace_id = 'turn-one'",
            (json.dumps(recipe),),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="failed integrity validation"):
        store.get_completion_evidence_snapshot("session", "turn-one")


def test_v9_header_evidence_requires_a_resident_binding() -> None:
    with pytest.raises(EvidenceCorrelationError, match="resident manager binding"):
        _validated_resident_binding(
            {"preflight_recipe_version": 9, "resident_manager_binding": None},
            {"host": "claude"},
            session_id="session",
        )


@pytest.mark.parametrize(
    ("outcomes", "expected"),
    [
        (["binding_conflict", "committed"], "committed"),
        (["binding_conflict", "binding_conflict"], "binding_conflict"),
    ],
)
def test_binding_conflict_replans_exactly_once(
    outcomes: list[str],
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ConflictStore:
        def __init__(self) -> None:
            self.calls = 0

        def mark_preflight_ready(self, **_kwargs: object) -> dict[str, str]:
            outcome = outcomes[self.calls]
            self.calls += 1
            return {"outcome": outcome}

        def plan_resident_manager_binding(
            self,
            *,
            session_id: str,
            host: str,
        ) -> object:
            return build_resident_manager_binding(
                session_id=session_id,
                host=host,
                delivery_mode="reused",
            )

    store = ConflictStore()
    recipe: dict[str, object] = {}
    rendered: list[dict[str, object]] = []
    monkeypatch.setattr(
        preflight_module,
        "_result_from_recipe",
        lambda _store, rendered_recipe, **_kwargs: rendered.append(dict(rendered_recipe)),
    )

    result = preflight_module._mark_ready_with_binding_replan(
        store,  # type: ignore[arg-type]
        session_id="session",
        trace_id="turn-one",
        attempt_token="attempt",
        recipe=recipe,  # type: ignore[arg-type]
        host="claude",
        routing_recipe={},
        specialist_refs=[],
        codex_native_plan_scopes=[],
        user_message="ping",
        config=AgencyConfig(),
        pipeline=object(),
    )

    assert result == {"outcome": expected}
    assert store.calls == 2
    assert len(rendered) == 1
    assert rendered[0]["resident_manager_binding"]["delivery_mode"] == "reused"
