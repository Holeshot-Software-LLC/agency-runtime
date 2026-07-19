"""Crash-safe authoritative terminal-finalization regressions."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from itertools import pairwise
from pathlib import Path

import pytest

from agency_runtime.core.store.schema import SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import harden_private_test_file


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _commit(
    store: Store,
    *,
    trace_id: str,
    response_hash: str,
    session_id: str = "session",
    action: str = "accept",
    status: str = "completed",
    expected_evidence_revision: int | None = None,
    policy_response_hash: str = "",
) -> dict[str, object]:
    if expected_evidence_revision is None:
        expected_evidence_revision = store.get_completion_evidence_snapshot(
            session_id,
            trace_id,
        )["evidence_revision"]
    return store.commit_terminal_finalization(
        session_id=session_id,
        trace_id=trace_id,
        host="test",
        action=action,
        response_hash=response_hash,
        policy_response_hash=policy_response_hash,
        status=status,
        expected_evidence_revision=expected_evidence_revision,
    )


def test_terminal_commit_binds_exact_response_and_exact_replay_only(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    store.record_finalization(
        trace_id="trace",
        host="test",
        action="continue",
        missing=["header"],
    )
    accepted_hash = _digest("accepted")

    committed = _commit(store, trace_id="trace", response_hash=accepted_hash)

    assert committed["outcome"] == "committed"
    assert committed["authoritative"] is True
    assert store.get_run("trace")["status"] == "completed"
    assert store.get_active_specialists_for_trace("session", "trace") == []
    [history] = store.get_specialist_load_history("session")
    assert history["expired_at"] is not None
    authoritative = store.get_authoritative_finalization(
        "session",
        "trace",
        action="accept",
        response_hash=accepted_hash,
    )
    assert authoritative is not None
    assert authoritative["id"] == committed["event_id"]
    assert authoritative["terminal_status"] == "completed"
    assert (
        store.find_authoritative_trace(
            "session",
            action="accept",
            response_hash=accepted_hash,
        )
        == "trace"
    )

    replay = _commit(store, trace_id="trace", response_hash=accepted_hash)
    conflict = _commit(store, trace_id="trace", response_hash=_digest("different"))

    assert replay["outcome"] == "replay"
    assert replay["authoritative"] is True
    assert replay["event_id"] == committed["event_id"]
    assert conflict["outcome"] == "conflict"
    assert conflict["authoritative"] is False
    assert (
        store.get_authoritative_finalization(
            "session",
            "trace",
            action="accept",
            response_hash=_digest("different"),
        )
        is None
    )
    assert store.has_finalization_action("trace", "continue") is True
    connection = store._connect()
    try:
        rows = connection.execute(
            "SELECT action, terminal_status FROM finalization_events "
            "WHERE trace_id = ? ORDER BY created_at, rowid",
            ("trace",),
        ).fetchall()
    finally:
        connection.close()
    assert [(row["action"], row["terminal_status"]) for row in rows] == [
        ("continue", None),
        ("accept", "completed"),
    ]


def test_terminal_commit_durably_binds_payload_and_policy_hashes(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    payload_hash = _digest('{"mediaUrl":"asset.png","text":"approved"}')
    policy_hash = _digest("approved")

    committed = _commit(
        store,
        trace_id="trace",
        response_hash=payload_hash,
        policy_response_hash=policy_hash,
    )

    assert committed["outcome"] == "committed"
    assert committed["response_hash"] == payload_hash
    assert committed["policy_response_hash"] == policy_hash
    authoritative = store.get_authoritative_finalization(
        "session",
        "trace",
        action="accept",
        response_hash=payload_hash,
        policy_response_hash=policy_hash,
    )
    assert authoritative is not None
    assert authoritative["response_hash"] == payload_hash
    assert authoritative["policy_response_hash"] == policy_hash
    assert (
        store.get_authoritative_finalization(
            "session",
            "trace",
            policy_response_hash=_digest("changed policy"),
        )
        is None
    )
    assert (
        store.find_authoritative_trace_by_policy_hash(
            "session",
            action="accept",
            policy_response_hash=policy_hash,
        )
        == "trace"
    )

    replay = _commit(
        store,
        trace_id="trace",
        response_hash=payload_hash,
        policy_response_hash=policy_hash,
    )
    changed_policy = _commit(
        store,
        trace_id="trace",
        response_hash=payload_hash,
        policy_response_hash=_digest("changed policy"),
    )

    assert replay["outcome"] == "replay"
    assert replay["authoritative"] is True
    assert changed_policy["outcome"] == "conflict"
    assert changed_policy["authoritative"] is False


def test_policy_hash_lookup_rejects_open_turn_then_selects_latest_exact_binding(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    policy_hash = _digest("same policy text")
    store.create_run(trace_id="trace-a", session_id="session")
    assert _commit(
        store,
        trace_id="trace-a",
        response_hash=_digest("payload-a"),
        policy_response_hash=policy_hash,
    )["authoritative"]
    assert (
        store.find_authoritative_trace_by_policy_hash(
            "session",
            policy_response_hash=policy_hash,
        )
        == "trace-a"
    )

    store.create_run(trace_id="trace-b", session_id="session")
    assert (
        store.find_authoritative_trace_by_policy_hash(
            "session",
            policy_response_hash=policy_hash,
        )
        is None
    )
    assert _commit(
        store,
        trace_id="trace-b",
        response_hash=_digest("payload-b"),
        policy_response_hash=policy_hash,
    )["authoritative"]
    assert (
        store.find_authoritative_trace_by_policy_hash(
            "session",
            policy_response_hash=policy_hash,
        )
        == "trace-b"
    )
    assert (
        store.find_authoritative_trace_by_policy_hash(
            "",
            policy_response_hash=policy_hash,
        )
        is None
    )


def test_concurrent_different_terminal_hashes_have_exactly_one_winner(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    hashes = (_digest("first"), _digest("second"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda response_hash: _commit(
                    store,
                    trace_id="trace",
                    response_hash=response_hash,
                ),
                hashes,
            )
        )

    assert sorted(result["outcome"] for result in results) == ["committed", "conflict"]
    [winner] = [result for result in results if result["authoritative"]]
    [loser] = [result for result in results if not result["authoritative"]]
    assert (
        store.get_authoritative_finalization(
            "session",
            "trace",
            action="accept",
            response_hash=str(winner["response_hash"]),
        )
        is not None
    )
    assert (
        store.get_authoritative_finalization(
            "session",
            "trace",
            action="accept",
            response_hash=str(loser["response_hash"]),
        )
        is None
    )
    connection = store._connect()
    try:
        terminal_count = connection.execute(
            "SELECT COUNT(*) FROM finalization_events "
            "WHERE trace_id = 'trace' AND terminal_status IS NOT NULL"
        ).fetchone()[0]
    finally:
        connection.close()
    assert terminal_count == 1


def test_concurrent_duplicate_continuations_share_one_retry_receipt(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    response_hash = _digest("blocked response")

    def claim() -> dict[str, str]:
        return store.claim_continuation(
            session_id="session",
            trace_id="trace",
            host="test",
            response_hash=response_hash,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: claim(), range(2)))

    assert sorted(result["outcome"] for result in results) == ["claimed", "replay"]
    assert len({result["receipt_id"] for result in results}) == 1
    connection = store._connect()
    try:
        rows = connection.execute(
            "SELECT id, response_hash FROM finalization_events "
            "WHERE trace_id = 'trace' AND action = 'continue'"
        ).fetchall()
    finally:
        connection.close()
    assert [(row["id"], row["response_hash"]) for row in rows] == [
        (results[0]["receipt_id"], response_hash)
    ]


def test_continuation_claim_exhausts_changed_response_or_explicit_retry(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    claimed = store.claim_continuation(
        session_id="session",
        trace_id="trace",
        host="test",
        response_hash=_digest("first response"),
    )

    changed = store.claim_continuation(
        session_id="session",
        trace_id="trace",
        host="test",
        response_hash=_digest("changed response"),
    )
    explicit_retry = store.claim_continuation(
        session_id="session",
        trace_id="trace",
        host="test",
        response_hash=_digest("first response"),
        retry_active=True,
    )

    assert claimed["outcome"] == "claimed"
    assert changed == {
        "outcome": "exhausted",
        "receipt_id": claimed["receipt_id"],
        "response_hash": _digest("changed response"),
    }
    assert explicit_retry["outcome"] == "exhausted"
    assert explicit_retry["receipt_id"] == claimed["receipt_id"]


def test_generic_legacy_continue_event_does_not_consume_host_retry(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    generic_id = store.record_finalization(
        trace_id="trace",
        host="generic",
        action="continue",
    )

    claimed = store.claim_continuation(
        session_id="session",
        trace_id="trace",
        host="native",
        response_hash=_digest("host response"),
    )

    assert claimed["outcome"] == "claimed"
    assert claimed["receipt_id"] != generic_id
    assert store.has_finalization_action("trace", "continue") is True


def test_terminal_commit_rejects_evidence_written_after_snapshot(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace",
        session_id="session",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    snapshot = store.get_completion_evidence_snapshot("session", "trace")

    assert snapshot["status"] == "active"
    assert snapshot["request_kind"] == "nontrivial"
    assert snapshot["specialists"] == ["reviewer"]
    assert snapshot["skills"] == []
    assert snapshot["model_receipt"] is None
    assert snapshot["delegations"] == []

    store.record_skill_loaded("session", "security-review", trace_id="trace")
    changed = store.get_completion_evidence_snapshot("session", "trace")
    assert changed["evidence_revision"] > snapshot["evidence_revision"]
    assert changed["skills"] == ["security-review"]

    stale = _commit(
        store,
        trace_id="trace",
        response_hash=_digest("stale response"),
        expected_evidence_revision=int(snapshot["evidence_revision"]),
    )

    assert stale["outcome"] == "stale_evidence"
    assert stale["authoritative"] is False
    run = store.get_run("trace")
    assert run["status"] == "active"
    assert run["ended_at"] is None
    connection = store._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM finalization_events WHERE trace_id = 'trace'"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT terminal_finalization_id FROM runs WHERE trace_id = 'trace'"
            ).fetchone()[0]
            is None
        )
    finally:
        connection.close()

    committed = _commit(
        store,
        trace_id="trace",
        response_hash=_digest("fresh response"),
        expected_evidence_revision=int(changed["evidence_revision"]),
    )
    assert committed["outcome"] == "committed"
    assert committed["authoritative"] is True


def test_completion_snapshot_and_terminal_cas_reject_corrupt_open_lifecycle(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET ended_at = '2026-07-14T00:00:00+00:00' WHERE trace_id = 'trace'"
        )
        revision = int(
            connection.execute(
                "SELECT evidence_revision FROM runs WHERE trace_id = 'trace'"
            ).fetchone()[0]
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="inconsistent terminal state"):
        store.get_completion_evidence_snapshot("session", "trace")
    rejected = _commit(
        store,
        trace_id="trace",
        response_hash=_digest("response"),
        expected_evidence_revision=revision,
    )
    assert rejected["outcome"] == "lifecycle_conflict"
    assert rejected["authoritative"] is False
    assert store.get_run("trace")["status"] == "active"
    assert store.get_authoritative_finalization("session", "trace") is None


def test_evidence_revision_advances_for_every_completion_evidence_family(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")

    def revision() -> int:
        return int(store.get_completion_evidence_snapshot("session", "trace")["evidence_revision"])

    observed = [revision()]
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="trace",
        request_fingerprint=_digest("request"),
        request_kind="nontrivial",
    )
    assert started["outcome"] == "started"
    observed.append(revision())

    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        requested_model="requested",
        resolved_model="resolved",
    )
    observed.append(revision())
    store.record_skill_loaded("session", "security-review", trace_id="trace")
    observed.append(revision())
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    observed.append(revision())
    event_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        work_unit_id="work-1",
        recommended_agent="reviewer",
    )
    observed.append(revision())
    store.update_delegation(
        event_id,
        status="completed",
        backend="worker",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )
    observed.append(revision())

    assert all(after > before for before, after in pairwise(observed))
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    assert snapshot["request_kind"] == "nontrivial"
    assert snapshot["model_receipt"]["resolved_model"] == "resolved"
    assert snapshot["skills"] == ["security-review"]
    assert snapshot["specialists"] == ["reviewer"]
    assert snapshot["delegations"][0]["status"] == "completed"


def test_terminal_commit_rolls_back_event_run_and_expiry_on_fault(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_terminal_expiry "
            "BEFORE UPDATE OF expired_at ON specialists_loaded "
            "WHEN NEW.trace_id = 'trace' "
            "BEGIN SELECT RAISE(ABORT, 'reject terminal expiry'); END"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="reject terminal expiry"):
        _commit(store, trace_id="trace", response_hash=_digest("response"))

    run = store.get_run("trace")
    assert run["status"] == "active"
    assert run["ended_at"] is None
    assert store.get_active_specialists_for_trace("session", "trace") == ["reviewer"]
    assert store.get_authoritative_finalization("session", "trace") is None
    connection = store._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM finalization_events WHERE trace_id = 'trace'"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()


def test_complete_run_cannot_rewrite_an_authoritatively_bound_terminal_run(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="trace", session_id="session")
    committed = _commit(
        store,
        trace_id="trace",
        response_hash=_digest("accepted"),
    )
    original = store.get_run("trace")

    store.complete_run(run_id, status="failed")

    assert store.get_run("trace") == original
    authoritative = store.get_authoritative_finalization(
        "session",
        "trace",
        action="accept",
        response_hash=_digest("accepted"),
    )
    assert authoritative is not None
    assert authoritative["id"] == committed["event_id"]
    with pytest.raises(ValueError, match="terminal status"):
        store.complete_run(run_id, status="active")
    assert store.get_run("trace") == original


def test_complete_run_closes_one_unbound_run_and_expires_specialists_once(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")

    store.complete_run(run_id, status="failed")
    first = store.get_run("trace")
    [first_load] = store.get_specialist_load_history("session")

    assert first["status"] == "failed"
    assert first["ended_at"] is not None
    assert first_load["expired_at"] is not None
    store.complete_run(run_id, status="completed")
    assert store.get_run("trace") == first
    assert store.get_specialist_load_history("session") == [first_load]


@pytest.mark.parametrize("status", ["", "active", "evidence_only"])
def test_complete_run_rejects_nonterminal_targets(tmp_path: Path, status: str) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="trace", session_id="session")

    with pytest.raises(ValueError, match="terminal status"):
        store.complete_run(run_id, status=status)

    assert store.get_run("trace")["status"] == "active"


def test_concurrent_complete_run_calls_cannot_rewrite_the_winner(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="trace", session_id="session")

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                lambda status: store.complete_run(run_id, status=status),
                ("failed", "stopped"),
            )
        )

    winner = store.get_run("trace")
    assert winner["status"] in {"failed", "stopped"}
    store.complete_run(run_id, status="superseded")
    assert store.get_run("trace") == winner


def test_complete_run_rolls_back_status_when_specialist_expiry_fails(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_complete_run_expiry "
            "BEFORE UPDATE OF expired_at ON specialists_loaded "
            "WHEN NEW.trace_id = 'trace' "
            "BEGIN SELECT RAISE(ABORT, 'reject complete run expiry'); END"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="reject complete run expiry"):
        store.complete_run(run_id, status="failed")

    assert store.get_run("trace")["status"] == "active"
    assert store.get_active_specialists_for_trace("session", "trace") == ["reviewer"]


def test_wrong_session_and_legacy_terminal_are_never_authorized(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="active", session_id="session")
    response_hash = _digest("response")

    wrong = _commit(
        store,
        trace_id="active",
        session_id="wrong-session",
        response_hash=response_hash,
        expected_evidence_revision=int(
            store.get_completion_evidence_snapshot("session", "active")["evidence_revision"]
        ),
    )

    assert wrong["outcome"] == "not_active"
    assert wrong["authoritative"] is False
    assert store.get_run("active")["status"] == "active"
    assert store.get_authoritative_finalization("wrong-session", "active") is None
    assert (
        store.find_authoritative_trace(
            "wrong-session",
            response_hash=response_hash,
        )
        is None
    )

    store.close_turn_evidence("session", "active", status="stopped")
    legacy_terminal = _commit(
        store,
        trace_id="active",
        response_hash=response_hash,
    )
    assert legacy_terminal["outcome"] == "not_active"
    assert legacy_terminal["authoritative"] is False


@pytest.mark.parametrize(
    ("action", "status"),
    [
        ("retry_exhausted", "retry_exhausted"),
        ("session_end", "session_ended"),
    ],
)
def test_all_terminal_outcomes_use_the_same_authoritative_binding(
    tmp_path: Path,
    action: str,
    status: str,
) -> None:
    store = Store(tmp_path / f"{status}.db")
    store.create_run(trace_id="trace", session_id="session")
    response_hash = _digest(status)

    committed = _commit(
        store,
        trace_id="trace",
        response_hash=response_hash,
        action=action,
        status=status,
    )

    assert committed["outcome"] == "committed"
    assert (
        store.get_authoritative_finalization(
            "session",
            "trace",
            action=action,
            response_hash=response_hash,
        )["terminal_status"]
        == status
    )
    assert (
        _commit(
            store,
            trace_id="trace",
            response_hash=response_hash,
            action=action,
            status=status,
        )["outcome"]
        == "replay"
    )
    assert store.close_turn_evidence("session", "trace", status="completed") == 0
    assert store.get_run("trace")["status"] == status


def test_authoritative_session_hash_lookup_selects_latest_exact_digest(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    response_hash = _digest("same response")
    for trace_id in ("trace-a", "trace-b"):
        store.create_run(trace_id=trace_id, session_id="session")
        assert _commit(
            store,
            trace_id=trace_id,
            response_hash=response_hash,
        )["authoritative"]

    assert store.find_authoritative_trace("session", response_hash=response_hash) == "trace-b"
    assert (
        store.find_authoritative_trace(
            "",
            response_hash=response_hash,
        )
        is None
    )


def test_retention_deletes_eligible_bound_terminal_pair_together(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="bound", session_id="session")
    _commit(
        store,
        trace_id="bound",
        response_hash=_digest("bound response"),
    )
    store.create_run(trace_id="unbound", session_id="session")
    store.record_finalization(
        trace_id="unbound",
        host="test",
        action="continue",
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE finalization_events SET created_at = '2000-01-01T00:00:01+00:00'"
        )
        connection.execute(
            "UPDATE runs SET started_at = '2000-01-01T00:00:00+00:00', "
            "ended_at = '2000-01-01T00:00:01+00:00' "
            "WHERE trace_id = 'bound'"
        )
        connection.execute(
            "UPDATE runs SET last_activity_at = '2000-01-01T00:00:01+00:00' "
            "WHERE trace_id = 'bound'"
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    assert report["tables"]["finalization_events"]["deleted"] == 1
    assert report["tables"]["runs"]["deleted"] == 1
    assert store.get_run("bound") is None
    assert store.get_authoritative_finalization("session", "bound") is None
    assert store.get_run("unbound")["status"] == "active"
    assert store.has_finalization_action("unbound", "continue") is True
    assert store.runtime_table_counts()["finalization_events"] == 1


def test_retention_preserves_bound_pair_when_fresh_child_keeps_parent(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="bound", session_id="session")
    store.record_model_receipt(
        trace_id="bound",
        session_id="session",
        ended_at="2100-01-01T00:00:00+00:00",
    )
    committed = _commit(
        store,
        trace_id="bound",
        response_hash=_digest("bound response"),
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET started_at = '2000-01-01T00:00:00+00:00', "
            "ended_at = '2000-01-01T00:00:01+00:00' WHERE trace_id = 'bound'"
        )
        connection.execute(
            "UPDATE finalization_events SET created_at = '2000-01-01T00:00:01+00:00' WHERE id = ?",
            (committed["event_id"],),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    assert report["tables"]["model_receipts"]["deleted"] == 0
    assert report["tables"]["finalization_events"]["deleted"] == 0
    assert report["tables"]["runs"]["deleted"] == 0
    assert store.get_authoritative_finalization("session", "bound") is not None


def test_terminal_pair_retention_dry_run_reports_joint_counts_without_deleting(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="bound", session_id="session")
    _commit(
        store,
        trace_id="bound",
        response_hash=_digest("bound response"),
    )

    report = store.trim_runtime_tables(keep_last=0, dry_run=True, vacuum=False)

    assert report["tables"]["finalization_events"]["deleted"] == 1
    assert report["tables"]["runs"]["deleted"] == 1
    assert report["remaining_tables"]["finalization_events"] == 1
    assert report["remaining_tables"]["runs"] == 1
    assert store.get_authoritative_finalization("session", "bound") is not None


@pytest.mark.parametrize("legacy_version", [13, 14])
def test_legacy_finalization_rows_migrate_unbound_and_never_authorize(
    tmp_path: Path,
    legacy_version: int,
) -> None:
    path = tmp_path / f"legacy-v{legacy_version}.db"
    connection = sqlite3.connect(path)
    response_hash_column = ", response_hash TEXT" if legacy_version >= 14 else ""
    connection.executescript(
        f"""
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES ({legacy_version});
        CREATE TABLE runs (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL UNIQUE,
            session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            user_message TEXT,
            metadata TEXT
        );
        CREATE TABLE finalization_events (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            host TEXT NOT NULL,
            action TEXT NOT NULL,
            missing TEXT
            {response_hash_column},
            created_at TEXT NOT NULL
        );
        INSERT INTO runs
            (id, trace_id, session_id, host, started_at, ended_at, status)
        VALUES
            ('legacy-run', 'legacy-trace', 'legacy-session', 'test',
             '2026-07-01T00:00:00+00:00', '2026-07-01T00:00:01+00:00',
             'completed');
        INSERT INTO finalization_events
            (id, trace_id, host, action, missing, created_at)
        VALUES
            ('legacy-event', 'legacy-trace', 'test', 'accept', NULL,
             '2026-07-01T00:00:01+00:00');
        """
    )
    connection.commit()
    connection.close()
    harden_private_test_file(path)

    store = Store(path)

    assert store.has_finalization_action("legacy-trace", "accept") is True
    assert (
        store.get_authoritative_finalization(
            "legacy-session",
            "legacy-trace",
            action="accept",
        )
        is None
    )
    assert (
        store.find_authoritative_trace(
            "legacy-session",
            response_hash=_digest("legacy"),
        )
        is None
    )
    connection = store._connect()
    try:
        run = connection.execute(
            "SELECT terminal_finalization_id FROM runs WHERE trace_id = 'legacy-trace'"
        ).fetchone()
        event = connection.execute(
            "SELECT response_hash, policy_response_hash, terminal_status "
            "FROM finalization_events "
            "WHERE id = 'legacy-event'"
        ).fetchone()
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        indexes = {
            str(row["name"]) for row in connection.execute("PRAGMA index_list(finalization_events)")
        }
    finally:
        connection.close()
    assert run["terminal_finalization_id"] is None
    assert event["response_hash"] is None
    assert event["policy_response_hash"] is None
    assert event["terminal_status"] is None
    assert version == SCHEMA_VERSION
    assert "idx_finalization_trace_response" in indexes
    assert "idx_finalization_trace_policy_response" in indexes


def test_current_v19_missing_policy_hash_index_is_repaired(tmp_path: Path) -> None:
    path = tmp_path / "damaged-v19.db"
    store = Store(path)
    connection = store._connect()
    try:
        connection.execute("DROP INDEX idx_finalization_trace_policy_response")
        connection.commit()
    finally:
        connection.close()

    repaired = Store(path)
    connection = repaired._connect()
    try:
        columns = {
            str(row["name"]) for row in connection.execute("PRAGMA table_info(finalization_events)")
        }
        indexes = {
            str(row["name"]) for row in connection.execute("PRAGMA index_list(finalization_events)")
        }
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    finally:
        connection.close()

    assert "policy_response_hash" in columns
    assert "idx_finalization_trace_policy_response" in indexes
    assert version == SCHEMA_VERSION


@pytest.mark.parametrize(
    "overrides",
    [
        {"session_id": ""},
        {"trace_id": ""},
        {"action": ""},
        {"status": "active"},
        {"response_hash": "not-a-digest"},
        {"policy_response_hash": "not-a-digest"},
        {"expected_evidence_revision": 0},
        {"expected_evidence_revision": True},
        {"expected_evidence_revision": "1"},
    ],
)
def test_terminal_commit_rejects_incomplete_or_nonterminal_identity(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    arguments = {
        "session_id": "session",
        "trace_id": "trace",
        "host": "test",
        "action": "accept",
        "response_hash": _digest("response"),
        "status": "completed",
        "expected_evidence_revision": store.get_completion_evidence_snapshot("session", "trace")[
            "evidence_revision"
        ],
    }
    arguments.update(overrides)

    with pytest.raises(ValueError):
        store.commit_terminal_finalization(**arguments)

    assert store.get_run("trace")["status"] == "active"
