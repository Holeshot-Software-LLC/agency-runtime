"""AR-398: a gap turn that outruns its preflight lease still leaves a receipt.

Two halves. The store's close is guarded by the attempt token alone and names
an expired lease on the receipt instead of dropping it; a token another attempt
holds is left to that attempt. The hiring loop stops proposing hires when the
lease cannot fit another round and says so per unit.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from types import SimpleNamespace

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.preflight import _with_hiring_deadline
from agency_runtime.core.preflight_failure import (
    HIRING_REASON_CODE_INVALID,
    PREFLIGHT_FAILURE_INVARIANTS,
    PREFLIGHT_LEASE_EXPIRED_BEFORE_CLOSE,
    default_preflight_failure_receipt,
    preflight_hiring_reason_codes,
    project_preflight_reason_codes,
)
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.pipeline import (
    HIRING_LEASE_BUDGET_EXHAUSTED,
    _hiring_round_fits,
    _run_gap_hiring,
)
from agency_runtime.core.store import schema as store_schema
from agency_runtime.core.store.sqlite import Store

_GAP = "no_safe_sufficient_team"
_ABSTAINED = "recruiter_abstained"
_PAST_LEASE = "2000-01-01T00:00:00.000000+00:00"


# --- the store's close ---------------------------------------------------------


def _start(store: Store, trace_id: str) -> str:
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id=trace_id,
        request_fingerprint=hashlib.sha256(trace_id.encode("utf-8")).hexdigest(),
        request_kind="nontrivial",
        host="claude",
    )
    assert started["outcome"] == "started"
    return str(started["attempt_token"])


def _receipt(invariant_code: str = "") -> dict:
    return {
        **default_preflight_failure_receipt(),
        "stage": "routing",
        "reason_code": "substantive_specialist_unavailable",
        "invariant_code": invariant_code,
        "staffing_reason_codes": [_GAP, _ABSTAINED],
        "hiring_reason_codes": ["hiring_status_not_attempted", HIRING_LEASE_BUDGET_EXHAUSTED],
    }


def _expire_lease(store: Store, trace_id: str) -> None:
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET preflight_lease_expires_at = ? WHERE trace_id = ?",
            (_PAST_LEASE, trace_id),
        )
        connection.commit()
    finally:
        connection.close()


def _run_row(store: Store, trace_id: str) -> dict:
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT status, preflight_state, preflight_attempt_token, preflight_lease_expires_at "
            "FROM runs WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
        return dict(row)
    finally:
        connection.close()


def _receipt_rows(store: Store, trace_id: str) -> list[dict]:
    connection = store._connect()
    try:
        rows = connection.execute(
            "SELECT host, stage, reason_code, invariant_code, hiring_reason_codes "
            "FROM preflight_failure_receipts WHERE trace_id = ? ORDER BY recorded_at",
            (trace_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def test_a_close_after_the_lease_expired_still_writes_the_receipt(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    token = _start(store, "late-close")
    _expire_lease(store, "late-close")

    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="late-close",
        attempt_token=token,
        failure_receipt=_receipt(),
    )

    run = _run_row(store, "late-close")
    assert run["status"] == "preflight_failed"
    assert run["preflight_state"] == ""
    assert run["preflight_attempt_token"] is None
    [receipt] = _receipt_rows(store, "late-close")
    assert receipt["host"] == "claude"
    assert receipt["reason_code"] == "substantive_specialist_unavailable"
    assert receipt["invariant_code"] == PREFLIGHT_LEASE_EXPIRED_BEFORE_CLOSE
    assert HIRING_LEASE_BUDGET_EXHAUSTED in receipt["hiring_reason_codes"]


def test_a_close_inside_the_lease_names_no_lifecycle_invariant(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    token = _start(store, "timely-close")

    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="timely-close",
        attempt_token=token,
        failure_receipt=_receipt(),
    )

    [receipt] = _receipt_rows(store, "timely-close")
    assert receipt["invariant_code"] == ""
    assert _run_row(store, "timely-close")["status"] == "preflight_failed"


def test_a_stronger_invariant_is_kept_over_the_expired_lease(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    token = _start(store, "scoped-close")
    _expire_lease(store, "scoped-close")

    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="scoped-close",
        attempt_token=token,
        failure_receipt=_receipt("native_plan_scope_invalid"),
    )

    [receipt] = _receipt_rows(store, "scoped-close")
    assert receipt["invariant_code"] == "native_plan_scope_invalid"


def test_a_superseded_token_leaves_the_run_alone_and_writes_no_receipt(tmp_path: Path) -> None:
    """Recovery replaces the token, so a stale token is another attempt's run.

    That attempt writes the turn's account itself; this one must touch nothing
    and say so through its return value.
    """

    store = Store(tmp_path / "agency.db")
    token = _start(store, "superseded")

    closed = store.fail_preflight_attempt(
        session_id="session",
        trace_id="superseded",
        attempt_token="someone-elses-token",
        failure_receipt=_receipt(),
    )

    assert closed is False
    run = _run_row(store, "superseded")
    assert run["status"] == "active"
    assert run["preflight_state"] == "in_progress"
    assert run["preflight_attempt_token"] == token
    assert _receipt_rows(store, "superseded") == []


def _legacy_receipts_ddl() -> str:
    table_sql, _triggers = store_schema._preflight_failure_receipts_statements()
    legacy = re.sub(
        r"CHECK \(invariant_code IN \([^)]*\)\)",
        "CHECK (invariant_code IN ('', 'native_plan_scope_invalid'))",
        table_sql,
        flags=re.S,
    )
    assert store_schema._PREFLIGHT_FAILURE_INVARIANT_LEGACY_CHECK in legacy
    return legacy.replace("CREATE TABLE IF NOT EXISTS", "CREATE TABLE", 1)


def test_a_store_built_before_schema_49_is_rebuilt_to_accept_the_new_invariant(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    token = _start(store, "legacy-row")
    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="legacy-row",
        attempt_token=token,
        failure_receipt=_receipt(),
    )
    connection = store._connect()
    try:
        # Put the pre-49 table back, rows and triggers included, and roll the
        # recorded version back so the next open must migrate.
        rows = connection.execute("SELECT * FROM preflight_failure_receipts").fetchall()
        connection.execute("DROP TABLE preflight_failure_receipts")
        connection.execute(_legacy_receipts_ddl())
        columns = rows[0].keys()
        connection.executemany(
            "INSERT INTO preflight_failure_receipts ("
            + ", ".join(columns)
            + ") VALUES ("
            + ", ".join("?" for _ in columns)
            + ")",
            [tuple(row) for row in rows],
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (48)")
        connection.commit()
        legacy_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'preflight_failure_receipts'"
        ).fetchone()["sql"]
        assert store_schema._PREFLIGHT_FAILURE_INVARIANT_LEGACY_CHECK in legacy_sql
    finally:
        connection.close()

    reopened = Store(path)
    connection = reopened._connect()
    try:
        rebuilt_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'preflight_failure_receipts'"
        ).fetchone()["sql"]
        assert PREFLIGHT_LEASE_EXPIRED_BEFORE_CLOSE in rebuilt_sql
        assert store_schema._PREFLIGHT_FAILURE_INVARIANT_LEGACY_CHECK not in rebuilt_sql
        triggers = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND tbl_name = 'preflight_failure_receipts'"
            )
        }
        # The scope and immutability triggers came back with the table; the
        # activity triggers are recreated by the open as before.
        assert {
            "agency_preflight_failure_scope_insert",
            "agency_preflight_failure_immutable",
        } <= triggers
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        assert version == store_schema.SCHEMA_VERSION
    finally:
        connection.close()
    # The legacy row survived the rebuild, and the widened vocabulary is live.
    [kept] = _receipt_rows(reopened, "legacy-row")
    assert kept["invariant_code"] == ""
    late_token = _start(reopened, "late-after-migration")
    _expire_lease(reopened, "late-after-migration")
    assert reopened.fail_preflight_attempt(
        session_id="session",
        trace_id="late-after-migration",
        attempt_token=late_token,
        failure_receipt=_receipt(),
    )
    [late] = _receipt_rows(reopened, "late-after-migration")
    assert late["invariant_code"] == PREFLIGHT_LEASE_EXPIRED_BEFORE_CLOSE


def test_the_new_lifecycle_code_is_inside_the_closed_vocabularies() -> None:
    assert PREFLIGHT_LEASE_EXPIRED_BEFORE_CLOSE in PREFLIGHT_FAILURE_INVARIANTS
    assert project_preflight_reason_codes([HIRING_LEASE_BUDGET_EXHAUSTED]) == [
        HIRING_LEASE_BUDGET_EXHAUSTED
    ]


# --- the hiring loop -----------------------------------------------------------


def _reason(code: str, unit_id: str = "") -> SimpleNamespace:
    return SimpleNamespace(code=code, unit_id=unit_id)


def _outcome(units: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(
        plan=SimpleNamespace(units=tuple(SimpleNamespace(unit_id=u) for u in units)),
        staffing=SimpleNamespace(
            abstention_reasons=(*(_reason(_GAP, u) for u in units), _reason(_ABSTAINED))
        ),
        proposal=SimpleNamespace(
            units=tuple(
                SimpleNamespace(unit_id=u, abstention_reasons=("inference-declared-gap",))
                for u in units
            )
        ),
        inference_mode="inferred",
        attempts=(SimpleNamespace(status="applied"),),
    )


def _request(deadline: float | None) -> pipeline._RouteRequest:
    return pipeline._RouteRequest(
        session_id="session",
        trace_id="trace",
        user_message="Write a COBOL batch program with JCL for z/OS",
        catalog=[],
        workforce_catalog=[],
        config=AgencyConfig(),
        policy={},
        context_fingerprint="fingerprint",
        routing_query="cobol batch",
        cache_key="cache",
        source_message_hash="hash",
        active_ids=frozenset(),
        host="claude",
        platform="linux",
        available_tools=("shell",),
        hiring_deadline_monotonic=deadline,
    )


def _abstained_hire() -> SimpleNamespace:
    return SimpleNamespace(
        status="abstained",
        reason_codes=("hiring_inference_unavailable",),
        hiring_case=None,
        worker=None,
        notification="",
        attempts=(),
        pending_commit=None,
        workforce_changed=False,
    )


def _drive(monkeypatch, *, deadline: float | None, clock: dict | None = None):
    calls: list[str] = []

    def fake_hire(request, unit, contracts, **_kwargs):
        calls.append(unit.unit_id)
        if clock is not None:
            clock["now"] += 100.0
        return _abstained_hire()

    monkeypatch.setattr("agency_runtime.core.workforce.hiring.hire_contractor_for_gap", fake_hire)
    if clock is not None:
        monkeypatch.setattr(pipeline, "time", SimpleNamespace(monotonic=lambda: clock["now"]))
    snapshot = SimpleNamespace(generation=1, contracts=())
    _, _snapshot, _catalog, events = _run_gap_hiring(
        _outcome(("u1", "u2", "u3")),
        _request(deadline),
        AgencyConfig(),
        SimpleNamespace(),
        snapshot,
        [],
        defer_commits=True,
    )
    return calls, events


def test_a_lease_that_is_already_spent_proposes_nothing_and_says_so(monkeypatch) -> None:
    calls, events = _drive(monkeypatch, deadline=pipeline.time.monotonic() - 1.0)

    assert calls == []
    assert [event["unit_id"] for event in events] == ["u1", "u2", "u3"]
    assert all(event["status"] == "not_attempted" for event in events)
    assert all(event["reason_codes"] == [HIRING_LEASE_BUDGET_EXHAUSTED] for event in events)
    codes = preflight_hiring_reason_codes({"hiring_events": events})
    assert "hiring_status_not_attempted" in codes
    assert HIRING_LEASE_BUDGET_EXHAUSTED in codes


def test_a_lease_with_room_lets_every_round_run(monkeypatch) -> None:
    calls, events = _drive(monkeypatch, deadline=pipeline.time.monotonic() + 3600.0)

    assert calls == ["u1", "u2", "u3"]
    assert all(event["status"] == "abstained" for event in events)
    assert not any(HIRING_LEASE_BUDGET_EXHAUSTED in event["reason_codes"] for event in events)


def test_no_lease_means_no_budget(monkeypatch) -> None:
    calls, _events = _drive(monkeypatch, deadline=None)

    assert calls == ["u1", "u2", "u3"]


def test_the_longest_measured_round_raises_the_bar_for_the_next(monkeypatch) -> None:
    clock = {"now": 1000.0}
    calls, events = _drive(monkeypatch, deadline=1000.0 + 150.0, clock=clock)

    # Round one fits (nothing measured yet), costs 100 s. Round two would need
    # at least another 100 s plus the margin against 50 s left, so it stops.
    assert calls == ["u1"]
    by_unit = {event["unit_id"]: event for event in events}
    assert by_unit["u1"]["status"] == "abstained"
    assert by_unit["u2"]["reason_codes"] == [HIRING_LEASE_BUDGET_EXHAUSTED]
    assert by_unit["u3"]["reason_codes"] == [HIRING_LEASE_BUDGET_EXHAUSTED]


def test_a_round_fits_only_with_the_margin_to_spare() -> None:
    now = pipeline.time.monotonic()
    assert _hiring_round_fits(now + 100.0, floor_seconds=30.0, longest_seconds=0.0)
    assert not _hiring_round_fits(now + 35.0, floor_seconds=30.0, longest_seconds=0.0)
    assert not _hiring_round_fits(now + 100.0, floor_seconds=30.0, longest_seconds=95.0)


# --- the preflight binds the lease to the request --------------------------------


def test_the_preflight_binds_its_lease_to_the_request() -> None:
    request = _request(None)
    bound = _with_hiring_deadline(request, 1234.5)
    assert bound.hiring_deadline_monotonic == 1234.5
    assert bound.routing_query == request.routing_query
    assert request.hiring_deadline_monotonic is None


def test_a_request_of_another_shape_passes_through_untouched() -> None:
    foreign = SimpleNamespace(context_fingerprint="x")
    assert _with_hiring_deadline(foreign, 5.0) is foreign


# --- the receipt carries every hiring code it can, one code at a time ----------


def _event(*codes: object, status: str = "abstained", calls_used: int = 1) -> dict:
    return {
        "unit_id": "u1",
        "status": status,
        "reason_codes": list(codes),
        "case_id": "",
        "worker": "",
        "version": "",
        "notification": "",
        "calls_used": calls_used,
    }


def test_a_colon_code_from_the_hiring_module_no_longer_silences_the_account() -> None:
    codes = preflight_hiring_reason_codes(
        {
            "hiring_events": [
                _event("hiring_inference_failed", "contract_invalid:causing_unit_coverage")
            ]
        }
    )
    assert codes == [
        "hiring_status_abstained",
        "hiring_inference_attempted",
        "hiring_inference_failed",
        "contract_invalid_causing_unit_coverage",
    ]


def test_a_code_that_cannot_be_carried_is_named_not_dropped_with_the_rest() -> None:
    codes = preflight_hiring_reason_codes(
        {"hiring_events": [_event("hiring_inference_failed", "", {"nested": 1}, "9lives")]}
    )
    assert codes == [
        "hiring_status_abstained",
        "hiring_inference_attempted",
        "hiring_inference_failed",
        HIRING_REASON_CODE_INVALID,
    ]


def test_clean_hiring_codes_project_exactly_as_before() -> None:
    codes = preflight_hiring_reason_codes(
        {
            "hiring_events": [
                _event("daily_hiring_limit_reached", status="not_attempted", calls_used=0)
            ]
        }
    )
    assert codes == ["hiring_status_not_attempted", "daily_hiring_limit_reached"]
