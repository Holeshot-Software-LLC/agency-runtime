"""AR-371: a turn that received the steward must not report 'loaded: none'.

The operator caught the header claiming `Agency/Agencies loaded: none` on
turns whose context visibly carried
`[Agency resident managers active; ... managers=agency-steward]`. Measured
2026-09-02: `agency-steward` appeared in 0 of 559 `specialists_loaded` rows,
and the session's binding row was pinned at `delivery_state=pending` on a
trace that had long since closed -- so AR-367's exact-trace projection
returned nothing and every later turn in that session reported none.

These tests pin the honest behaviour: a fail-open turn names the steward,
and it keeps naming it after an acknowledgement has stalled on an older
trace.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.resident_managers import RESIDENT_MANAGER_SLUGS
from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.store import resident_binding as resident_binding_store
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _materialized_master_control(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _fail_open_turn(store: Store, *, session_id: str, trace_id: str, host: str = "claude") -> None:
    """Drive one turn through preflight into the fail-open close."""

    store.create_run(
        trace_id=trace_id,
        session_id=session_id,
        host=host,
        metadata={"request_kind": "nontrivial"},
    )
    attempt = store.begin_preflight_attempt(
        session_id=session_id,
        trace_id=trace_id,
        request_fingerprint=sha256(trace_id.encode("utf-8")).hexdigest(),
        request_kind="nontrivial",
        host=host,
    )
    token = attempt["attempt_token"] if isinstance(attempt, dict) else str(attempt)
    binding = store.plan_resident_manager_binding(session_id=session_id, host=host)
    assert store.fail_preflight_attempt(
        session_id=session_id,
        trace_id=trace_id,
        attempt_token=token,
        resident_manager_binding=binding,
    )


def test_a_fail_open_turn_names_the_steward_it_was_given(tmp_path: Path) -> None:
    store = _persistent_store(tmp_path / "steward.db")
    session_id = "ar371-session"
    _fail_open_turn(store, session_id=session_id, trace_id="ar371-turn")

    snapshot = store.get_completion_evidence_snapshot(session_id, "ar371-turn")

    assert list(snapshot["resident_managers"]) == list(RESIDENT_MANAGER_SLUGS)
    # fill_header_fields renders ", ".join(resident_managers + specialists)
    # for this field, so a non-empty projection is a non-"none" header.
    assert snapshot["resident_managers"], "the header would report none"


def test_a_stalled_acknowledgement_does_not_silence_later_turns(tmp_path: Path) -> None:
    """The measured shape: one claim pinned to a dead trace, session-wide 'none'."""

    store = _persistent_store(tmp_path / "stalled.db")
    session_id = "ar371-stalled"
    # First turn claims the binding and is never acknowledged.
    _fail_open_turn(store, session_id=session_id, trace_id="ar371-stalled-first")
    # A later turn in the same session cannot claim what is already pinned.
    _fail_open_turn(store, session_id=session_id, trace_id="ar371-stalled-later")

    later = store.get_completion_evidence_snapshot(session_id, "ar371-stalled-later")

    assert list(later["resident_managers"]) == list(RESIDENT_MANAGER_SLUGS)
    assert later["resident_managers"], "a stalled ack would report none"


def test_a_request_scoped_host_is_left_to_prove_delivery_per_request(tmp_path: Path) -> None:
    """Hermes delivers per request, so it is never covered by this fallback."""

    store = Store(tmp_path / "hermes.db")
    conn = store._connect()
    try:
        assert (
            store.delivered_resident_manager_slugs(
                conn,
                session_id="ar371-hermes",
                host="hermes",
                run_status="preflight_failed",
            )
            == ()
        )
        # A turn that did not fail open is not covered either: this fallback
        # only describes the capsule the fail-open path actually delivered.
        assert (
            store.delivered_resident_manager_slugs(
                conn,
                session_id="ar371-hermes",
                host="claude",
                run_status="completed",
            )
            == ()
        )
    finally:
        conn.close()


@pytest.mark.parametrize("status", ["completed", "response_invalid", "active"])
def test_only_a_fail_open_close_claims_delivery(tmp_path: Path, status: str) -> None:
    store = Store(tmp_path / f"status-{status}.db")
    conn = store._connect()
    try:
        assert (
            store.delivered_resident_manager_slugs(
                conn,
                session_id="ar371-status",
                host="claude",
                run_status=status,
            )
            == ()
        )
    finally:
        conn.close()
