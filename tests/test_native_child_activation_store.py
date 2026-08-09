from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path

import pytest

from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store import delegation_activation as activation_store
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import stub_inference_invoker, write_provider_config


def _isolated_turn(path: Path) -> tuple[Store, str, str]:
    # ADR-0087: selection runs inference only when a provider is configured.
    config_path = path.parent / "agency.yaml"
    write_provider_config(config_path)
    os.environ["AGENCY_CONFIG_PATH"] = str(config_path)
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    store = Store(path)
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        result = run_preflight(
            store,
            session_id="session",
            trace_id="trace",
            user_message="Review and refactor this Python code for security and correctness",
            host="codex",
            capability_receipt=native_adapter_capability_receipt(
                "codex",
                platform="windows" if os.name == "nt" else "linux",
                session_id="session",
                trace_id="trace",
            ),
        )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        os.environ.pop("AGENCY_CONFIG_PATH", None)
        reset_config_cache()
    slug = next(
        candidate
        for candidate in result.selected_specialists
        if candidate not in PROTECTED_AGENT_SLUGS
    )
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    planned = next(row for row in snapshot["unit_agent_plan"] if row["recommended_agent"] == slug)
    return store, slug, str(planned["work_unit_id"])


def _prepare(store: Store, slug: str, unit: str, **changes: object) -> dict[str, object]:
    return store.prepare_delegation_activation(
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=unit,
        **changes,
    )


def _consume(
    store: Store,
    prepared: dict[str, object],
    slug: str,
    unit: str,
    *,
    worker_id: str = "worker-1",
    native_run_id: str = "run-1",
) -> dict[str, object]:
    return store.consume_delegation_activation(
        activation_token=str(prepared["activation_token"]),
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=unit,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )


def test_legacy_consumed_projection_remains_reciprocally_attachable(tmp_path: Path) -> None:
    store = Store(tmp_path / "legacy-attach.db")
    store.create_run(trace_id="legacy-trace", session_id="legacy-session", host="codex")
    event_id = store.record_delegation(
        trace_id="legacy-trace",
        session_id="legacy-session",
        host="codex",
        work_unit_id="legacy-unit",
        recommended_agent="code-reviewer",
        status="delegated",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="legacy-worker",
        native_run_id="legacy-run",
    )
    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "('legacy-receipt', ?, 'legacy-session', 'legacy-trace', 'legacy-unit', "
            "'code-reviewer', '1.0.0', ?, 'generic-worker', '', '', 'created', 'consumed')",
            ("a" * 64, "b" * 64),
        )
        activation_store.attach_consumed_activation_to_delegation(
            connection,
            event_id=event_id,
            trace_id="legacy-trace",
            work_unit_id="legacy-unit",
        )
        connection.commit()
        event = connection.execute(
            "SELECT activation_receipt_id FROM delegation_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        receipt = connection.execute(
            "SELECT delegation_event_id, worker_id, native_run_id "
            "FROM delegation_activation_receipts WHERE id = 'legacy-receipt'"
        ).fetchone()
    finally:
        connection.close()

    assert event["activation_receipt_id"] == "legacy-receipt"
    assert receipt["delegation_event_id"] == event_id
    assert receipt["worker_id"] == "legacy-worker"
    assert receipt["native_run_id"] == "legacy-run"


def test_native_child_end_runs_auto_promotion_policy_in_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live outcome path participates in the automatic-promotion policy.

    Recording a native child's terminal outcome must evaluate the configured
    promotion policy in the same transaction (a no-op for workers without
    receipt-validated acceptance evidence, but never dead code)."""

    from agency_runtime.core.store import workforce as store_workforce
    from agency_runtime.core.workforce.known_installer import install_known_contractors

    store = Store(tmp_path / "auto-promote-live.db")
    install_known_contractors(store)
    slug = "python-application-engineer"
    worker_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    native_run_id = f"codex-agent:{worker_id}"
    unit = "unit-live"
    store.create_run(trace_id="trace", session_id="session", host="codex")
    event_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="codex",
        work_unit_id=unit,
        recommended_agent=slug,
        status="delegated",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id=worker_id,
        native_run_id=native_run_id,
    )
    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "('live-receipt', ?, 'session', 'trace', ?, ?, "
            "'1.0.0', ?, 'generic-worker', '', '', 'created', 'consumed')",
            ("a" * 64, unit, slug, "b" * 64),
        )
        activation_store.attach_consumed_activation_to_delegation(
            connection,
            event_id=event_id,
            trace_id="trace",
            work_unit_id=unit,
        )
        connection.commit()
    finally:
        connection.close()

    calls: list[str] = []
    original = store_workforce._auto_promote_if_ready

    def spy(conn: object, worker: object, **kwargs: object) -> None:
        calls.append(str(worker["agent_slug"]))
        original(conn, worker, **kwargs)

    monkeypatch.setattr(store_workforce, "_auto_promote_if_ready", spy)
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        work_unit_id=unit,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    ended = store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        work_unit_id=unit,
        worker_id=worker_id,
        native_run_id=native_run_id,
        outcome="ok",
    )

    assert ended["ended_at"]
    assert calls == [slug]
    # Assignment events carry no verifier evidence, so the policy never
    # promotes on the live path until verified acceptances exist.
    with closing(store._connect()) as conn:
        contractor = conn.execute(
            "SELECT employment_class FROM agent_workers WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
    assert contractor is not None
    assert contractor["employment_class"] == "contractor"
