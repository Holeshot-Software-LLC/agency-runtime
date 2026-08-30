"""Preflight failure-receipt migration coverage.

This file previously also carried two Codex delegation-plan proofs -- an atomic
`native_plan_scope_invalid` failure and an exact-path replay through ready
commit. Both were retired with the rest of the Job B proof harness (see
`a3e359b4`): they could only fire once a unit-agent plan existed, and the
deterministic staffing default is now `delivery="load"`, so no plan is built
unless inference explicitly asks to delegate. Redaction of a failed preflight --
the part of that coverage worth keeping -- lives in
`test_canary_activation_snapshot_projects_exact_preflight_failure`.
"""

from __future__ import annotations

from pathlib import Path

from agency_runtime.core.store.sqlite import Store


def test_schema_v42_adds_empty_invariant_to_existing_failure_receipts(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    started = store.begin_preflight_attempt(
        session_id="migration-session",
        trace_id="migration-trace",
        request_fingerprint="a" * 64,
        request_kind="nontrivial",
        host="codex",
    )
    assert store.fail_preflight_attempt(
        session_id="migration-session",
        trace_id="migration-trace",
        attempt_token=started["attempt_token"],
    )
    connection = store._connect()
    try:
        connection.execute("ALTER TABLE preflight_failure_receipts DROP COLUMN invariant_code")
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (41)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    receipt = migrated.get_preflight_failure_receipt(
        "migration-session",
        "migration-trace",
    )

    assert receipt is not None
    assert receipt["schema_version"] == "agency.preflight.failure.v3"
    assert receipt["invariant_code"] == ""
