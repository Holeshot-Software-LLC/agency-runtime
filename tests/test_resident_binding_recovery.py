"""AR-371: reclaim only an older closed delivery, never its acknowledgment."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.resident_manager_binding import ResidentManagerBinding
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_SLUGS
from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.store import preflight as preflight_store
from agency_runtime.core.store import resident_binding as subject
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _stable_master(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = RuntimeControlSnapshot(
        schema_version=1,
        enabled=True,
        generation=0,
        updated_at="2026-07-17T00:00:00Z",
        source="test",
        materialized=True,
    )
    monkeypatch.setattr(subject, "read_effective_runtime_control_snapshot", lambda **_k: snapshot)


def _store(path: Path) -> Store:
    store = Store(path)
    store.set_host_control("claude", enabled=False, expected_generation=0, source="test")
    store.set_host_control("claude", enabled=True, expected_generation=1, source="test")
    return store


def _begin(store: Store, trace: str, *, session: str = "session", host: str = "claude") -> str:
    return store.begin_preflight_attempt(
        session_id=session,
        trace_id=trace,
        host=host,
        request_fingerprint=sha256(trace.encode()).hexdigest(),
        request_kind="nontrivial",
    )["attempt_token"]


def _row(store: Store) -> dict[str, Any]:
    conn = store._connect()
    try:
        return dict(subject._binding_row(conn, session_id="session", host="claude"))
    finally:
        conn.close()


def _claim(store: Store, trace: str, binding: ResidentManagerBinding) -> bool:
    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        result = store._commit_resident_manager_binding(
            conn, session_id="session", trace_id=trace, binding=binding
        )
        conn.commit() if result else conn.rollback()
        return result
    finally:
        conn.close()


def _fail(store: Store, trace: str) -> ResidentManagerBinding:
    token = _begin(store, trace)
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id=trace,
        attempt_token=token,
        resident_manager_binding=binding,
    )
    return binding


def _ready(store: Store, trace: str, token: str, binding: ResidentManagerBinding) -> dict[str, str]:
    """Use the real ready transaction and content-free recipe validation."""

    routing = {
        "query_hash": "a" * 64,
        "context_fingerprint": "b" * 64,
        "status": "abstained",
        "source": "test",
        "selected_ids": [],
        "work_units": {"delegate": False, "count": 1, "confidence": "low", "source": "test"},
    }
    projected = preflight_store._project_routing_evidence(routing, trace_id=trace)
    assert projected is not None
    recipe = {
        "recipe_version": preflight_store.PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": "c" * 64,
        "host": "claude",
        "delivery_mode": "direct",
        "context_limit": 4096,
        "routing": projected["decision"],
        "specialist_refs": [],
        "selection_refs": [],
        "unit_assignment_agents": [],
        "trivial": False,
        "roster_size": 0,
        "roster_generation": 0,
        "resident_manager_binding": binding.as_dict(),
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test"],
            "state_revision": "a" * 64,
            "classifier_version": 1,
        },
    }
    return store.mark_preflight_ready(
        session_id="session",
        trace_id=trace,
        attempt_token=token,
        recipe=recipe,
        host="claude",
        routing_evidence=routing,
        specialist_refs=[],
    )


@pytest.mark.parametrize("path", ["ready", "fail_open"])
def test_later_turn_claims_closed_pending_delivery_without_acknowledging_it(
    tmp_path: Path, path: str
) -> None:
    store = _store(tmp_path / "recovery.db")
    old = _fail(store, "old")
    before = _row(store)
    token = _begin(store, "new")
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert binding.requires_kernel_injection
    if path == "ready":
        assert _ready(store, "new", token, binding) == {"outcome": "committed"}
    else:
        assert store.fail_preflight_attempt(
            session_id="session",
            trace_id="new",
            attempt_token=token,
            resident_manager_binding=binding,
        )
    after = _row(store)
    assert after["pending_trace_id"] == after["last_trace_id"] == "new"
    assert after["delivery_state"] == "pending"
    for field in (
        "binding_id",
        "kernel_hash",
        "pending_delivery_mode",
        "pending_restore_generation",
    ):
        assert after[field] == before[field]
    snapshot = store.get_completion_evidence_snapshot("session", "new")
    assert snapshot["resident_managers"] == list(RESIDENT_MANAGER_SLUGS)
    assert not store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="old", binding=old
    )
    assert _row(store) == after
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="new", binding=binding
    )
    assert (
        store.plan_resident_manager_binding(session_id="session", host="claude").delivery_mode
        == "reused"
    )


def test_readers_do_not_reclaim_the_same_fail_open_turn_while_stop_is_pending(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "same-turn.db")
    binding = _fail(store, "current")
    before = _row(store)
    for _ in range(3):
        assert store.plan_resident_manager_binding(session_id="session", host="claude") == binding
        assert (
            store.pending_resident_manager_binding(
                session_id="session", host="claude", trace_id="current"
            )
            == binding.as_dict()
        )
    assert _row(store) == before
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="current", binding=binding
    )


def test_active_pending_turn_stays_owned_and_new_fail_open_close_still_lands(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "active.db")
    _begin(store, "old")
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _claim(store, "old", binding)
    before = _row(store)
    token = _begin(store, "new")
    assert _ready(store, "new", token, binding) == {"outcome": "binding_conflict"}
    assert store.fail_preflight_attempt(
        session_id="session", trace_id="new", attempt_token=token, resident_manager_binding=binding
    )
    assert store.get_run("new")["status"] == "preflight_failed"
    assert _row(store) == before


@pytest.mark.parametrize("status", sorted(subject._RECOVERABLE_TERMINAL_RUN_STATUSES))
def test_known_terminal_run_statuses_can_release_a_previous_claim(
    tmp_path: Path, status: str
) -> None:
    store = _store(tmp_path / "terminal.db")
    _begin(store, "old")
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _claim(store, "old", binding)
    assert store.close_turn_evidence("session", "old", status=status) == 1
    _begin(store, "new")
    assert _claim(store, "new", binding)
    assert _row(store)["delivery_state"] == "pending"


@pytest.mark.parametrize("fault", ["unknown_status", "missing_end", "malformed_end", "missing_run"])
def test_ambiguous_old_run_does_not_authorize_recovery(tmp_path: Path, fault: str) -> None:
    store = _store(tmp_path / "ambiguous.db")
    binding = _fail(store, "old")
    conn = store._connect()
    try:
        if fault == "missing_run":
            conn.execute("DELETE FROM runs WHERE trace_id = 'old'")
        elif fault == "unknown_status":
            conn.execute("UPDATE runs SET status = 'unknown_terminal' WHERE trace_id = 'old'")
        else:
            conn.execute(
                "UPDATE runs SET ended_at = ? WHERE trace_id = 'old'",
                (None if fault == "missing_end" else "not-a-timestamp",),
            )
        conn.commit()
    finally:
        conn.close()
    before = _row(store)
    _begin(store, "new")
    assert not _claim(store, "new", binding)
    assert _row(store) == before


@pytest.mark.parametrize("scope", ["old_session", "old_host", "new_session", "new_host"])
def test_recovery_requires_both_exact_session_and_canonical_host_runs(
    tmp_path: Path, scope: str
) -> None:
    store = _store(tmp_path / "scope.db")
    old_session = "other" if scope == "old_session" else "session"
    old_host = "codex" if scope == "old_host" else "claude"
    _begin(store, "old", session=old_session, host=old_host)
    binding = store.plan_resident_manager_binding(session_id="session", host="claude")
    assert _claim(store, "old", binding)
    assert store.close_turn_evidence(old_session, "old") == 1
    before = _row(store)
    _begin(
        store,
        "new",
        session="other" if scope == "new_session" else "session",
        host="codex" if scope == "new_host" else "claude",
    )
    assert not _claim(store, "new", binding)
    assert _row(store) == before


@pytest.mark.parametrize(
    ("status", "preflight_state", "ended_at"),
    [
        ("completed", "", "2026-09-07T00:00:00+00:00"),
        ("active", "", None),
        ("active", "in_progress", "2026-09-07T00:00:00+00:00"),
        ("preflight_failed", "", "invalid"),
    ],
)
def test_incoming_turn_must_be_at_its_own_valid_claim_boundary(
    tmp_path: Path, status: str, preflight_state: str, ended_at: str | None
) -> None:
    store = _store(tmp_path / "incoming.db")
    binding = _fail(store, "old")
    _begin(store, "new")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE runs SET status = ?, preflight_state = ?, ended_at = ? WHERE trace_id = 'new'",
            (status, preflight_state, ended_at),
        )
        conn.commit()
    finally:
        conn.close()
    before = _row(store)
    assert not _claim(store, "new", binding)
    assert _row(store) == before


@pytest.mark.parametrize("ordering", ["older_candidate", "newer_competitor"])
def test_recovery_is_strictly_forward_to_latest_turn(tmp_path: Path, ordering: str) -> None:
    store = _store(tmp_path / "ordering.db")
    if ordering == "older_candidate":
        _begin(store, "candidate")
    binding = _fail(store, "old")
    if ordering == "newer_competitor":
        _begin(store, "candidate")
        _begin(store, "latest")
    before = _row(store)
    assert not _claim(store, "candidate", binding)
    assert _row(store) == before


@pytest.mark.parametrize(
    ("retired_session", "retired_host", "retired_first", "permitted"),
    [
        ("session", "claude", False, False),
        ("session", "codex", False, False),
        ("other", "claude", False, True),
        ("session", "claude", True, True),
    ],
)
def test_retention_cannot_make_a_stale_candidate_current_again(
    tmp_path: Path,
    retired_session: str,
    retired_host: str,
    retired_first: bool,
    permitted: bool,
) -> None:
    store = _store(tmp_path / "retired-ordering.db")
    if retired_first:
        _begin(store, "retired", session=retired_session, host=retired_host)
    binding = _fail(store, "old")
    token = _begin(store, "candidate")
    if not retired_first:
        _begin(store, "retired", session=retired_session, host=retired_host)
    store.complete_run("retired", status="completed")
    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        retired = conn.execute(
            "SELECT trace_id, session_id, turn_sequence FROM runs WHERE trace_id = 'retired'"
        ).fetchone()
        assert (
            store._record_trace_tombstones(conn, [retired], retired_at="2026-09-07T00:00:00+00:00")
            == 1
        )
        conn.execute("DELETE FROM runs WHERE trace_id = 'retired'")
        conn.commit()
    finally:
        conn.close()
    before = _row(store)
    expected = "committed" if permitted else "binding_conflict"
    assert _ready(store, "candidate", token, binding) == {"outcome": expected}
    if permitted:
        assert _row(store)["pending_trace_id"] == "candidate"
    else:
        assert _row(store) == before


def test_stale_claim_and_late_stop_cannot_overwrite_the_new_owner(tmp_path: Path) -> None:
    store = _store(tmp_path / "cas.db")
    binding = _fail(store, "old")
    before = _row(store)
    state = subject._validate_current_row(before, binding)
    _begin(store, "new")
    assert _claim(store, "new", binding)
    claimed = _row(store)
    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        assert not store._commit_current_binding(
            conn, session_id="session", trace_id="new", binding=binding, state=state
        )
        conn.rollback()
    finally:
        conn.close()
    assert not _claim(store, "old", binding)
    assert not store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="old", binding=binding
    )
    assert _row(store) == claimed


def test_recovered_restore_does_not_consume_a_later_compaction_generation(tmp_path: Path) -> None:
    store = _store(tmp_path / "restore.db")
    initial = _fail(store, "initial")
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="initial", binding=initial
    )
    assert store.mark_resident_manager_restore_required(session_id="session", host="claude")
    pending = _fail(store, "old-restore")
    assert pending.delivery_mode == "restored"
    assert store.mark_resident_manager_restore_required(session_id="session", host="claude")
    replacement = _fail(store, "new-restore")
    row = _row(store)
    assert row["restore_generation"] == 2
    assert row["pending_restore_generation"] == 1
    assert row["applied_restore_generation"] == 0
    assert not store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="old-restore", binding=pending
    )
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="new-restore", binding=replacement
    )
    assert _row(store)["applied_restore_generation"] == 1
    assert (
        store.plan_resident_manager_binding(session_id="session", host="claude").delivery_mode
        == "restored"
    )


def test_old_epoch_binding_cannot_use_closed_turn_recovery(tmp_path: Path) -> None:
    store = _store(tmp_path / "epoch.db")
    binding = _fail(store, "old")
    store.set_host_control("claude", enabled=False, expected_generation=2, source="test")
    store.set_host_control("claude", enabled=True, expected_generation=3, source="test")
    _begin(store, "new")
    before = _row(store)
    assert not _claim(store, "new", binding)
    assert _row(store) == before


def test_stale_kernel_needs_fresh_injection_not_recovered_restore(tmp_path: Path) -> None:
    store = _store(tmp_path / "kernel.db")
    initial = _fail(store, "initial")
    assert store.acknowledge_resident_manager_binding(
        session_id="session", host="claude", trace_id="initial", binding=initial
    )
    assert store.mark_resident_manager_restore_required(session_id="session", host="claude")
    binding = _fail(store, "old")
    conn = store._connect()
    try:
        conn.execute("UPDATE resident_manager_bindings SET kernel_hash = ?", ("0" * 64,))
        conn.commit()
    finally:
        conn.close()
    _begin(store, "new")
    before = _row(store)
    assert binding.delivery_mode == "restored"
    assert not _claim(store, "new", binding)
    assert _row(store) == before
    assert (
        store.plan_resident_manager_binding(session_id="session", host="claude").delivery_mode
        == "injected"
    )
