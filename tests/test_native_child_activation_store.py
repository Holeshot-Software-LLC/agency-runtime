from __future__ import annotations

import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier

import pytest

from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.native_child_activation import (
    NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
    build_native_child_activation_grant,
    deserialize_native_child_activation_grant,
    deserialize_native_child_activation_receipt,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store import delegation_activation as activation_store
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call
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


def test_public_grant_and_consumption_are_exact_separate_and_evidence_gated(
    tmp_path: Path,
) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "ledger.db")
    prepared = _prepare(
        store,
        slug,
        unit,
        mutation_mode="workspace_write",
        mutation_path_prefixes=("agency_runtime/core/store",),
        evidence_contract_id="store-integration-v1",
        evidence_requirements=("delegation-execution", "specialist-load"),
    )

    connection = store._connect()
    try:
        grant_row = connection.execute(
            "SELECT * FROM delegation_activation_receipts WHERE id = ?",
            (prepared["receipt_id"],),
        ).fetchone()
        consumption_count = connection.execute(
            "SELECT COUNT(*) FROM delegation_activation_consumptions"
        ).fetchone()[0]
        loaded_count = connection.execute(
            "SELECT COUNT(*) FROM specialists_loaded WHERE trace_id = 'trace' AND agent_slug = ?",
            (slug,),
        ).fetchone()[0]
        event = connection.execute(
            "SELECT activation_receipt_id FROM delegation_events "
            "WHERE trace_id = 'trace' AND work_unit_id = ?",
            (unit,),
        ).fetchone()
    finally:
        connection.close()

    grant = deserialize_native_child_activation_grant(grant_row["grant_payload"])
    assert grant.as_dict() == prepared["activation_grant"]
    assert grant.grant_id == prepared["grant_id"]
    assert grant.version == 2
    assert grant.worker_binding is not None
    assert grant.worker_binding.as_dict() == {
        "mode": "late_bound",
        "worker_kind": "generic-worker",
        "worker_id": "",
    }
    assert grant.specialist.slug == slug
    assert grant.mutation_scope.as_dict() == {
        "mode": "workspace_write",
        "path_prefixes": ["agency_runtime/core/store"],
    }
    assert grant.evidence_contract.as_dict() == {
        "contract_id": "store-integration-v1",
        "requirements": ["delegation-execution", "specialist-load"],
    }
    assert (
        sha256(str(prepared["activation_token"]).encode("ascii")).hexdigest()
        == grant_row["token_hash"]
    )
    assert str(prepared["activation_token"]) not in grant_row["grant_payload"]
    assert "token_hash" not in grant.as_dict()
    assert consumption_count == loaded_count == 0
    assert event is None or event["activation_receipt_id"] is None

    connection = store._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="requires a consumption receipt"):
            connection.execute(
                "UPDATE delegation_activation_receipts SET consumed_at = 'forged' WHERE id = ?",
                (prepared["receipt_id"],),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="requires a valid receipt"):
            connection.execute(
                "INSERT INTO specialists_loaded "
                "(id, session_id, trace_id, agent_slug, loaded_at, activation_receipt_id) "
                "VALUES ('forged-load', 'session', 'trace', ?, 'forged', ?)",
                (slug, prepared["receipt_id"]),
            )
    finally:
        connection.rollback()
        connection.close()

    with pytest.raises(ValueError, match="complete child lineage"):
        store.consume_delegation_activation(
            activation_token=str(prepared["activation_token"]),
            session_id="session",
            trace_id="trace",
            specialist_slug=slug,
            work_unit_id=unit,
        )

    consumed = _consume(store, prepared, slug, unit)
    public_receipt = consumed["activation_receipt"]
    assert public_receipt["grant_id"] == grant.grant_id
    assert public_receipt["child_run"] == {
        "worker_kind": "generic-worker",
        "worker_id": "worker-1",
        "native_run_id": "run-1",
    }

    connection = store._connect()
    try:
        consumption = connection.execute(
            "SELECT * FROM delegation_activation_consumptions WHERE grant_id = ?",
            (grant.grant_id,),
        ).fetchone()
        loaded = connection.execute(
            "SELECT activation_receipt_id FROM specialists_loaded "
            "WHERE trace_id = 'trace' AND agent_slug = ?",
            (slug,),
        ).fetchone()
    finally:
        connection.close()
    stored_receipt = deserialize_native_child_activation_receipt(
        consumption["receipt_payload"],
        grant=grant,
    )
    assert stored_receipt.as_dict() == public_receipt
    assert consumption["legacy_activation_receipt_id"] == prepared["receipt_id"]
    assert loaded["activation_receipt_id"] == prepared["receipt_id"]

    with pytest.raises(ValueError, match="already consumed"):
        _consume(store, prepared, slug, unit)

    mark_delegation_executed(
        store,
        session_id="session",
        trace_id="trace",
        host="codex",
        backend="spawn_agent",
        agent="generic-worker",
        work_unit_id=unit,
        executed_worker_kind="generic-worker",
        executed_worker_id="different-worker",
        native_run_id="different-run",
    )
    unlinked = store.get_delegations("trace")[0]
    assert unlinked["activation_receipt_id"] is None

    connection = store._connect()
    try:
        connection.execute(
            "UPDATE delegation_events SET executed_worker_id = 'worker-1', "
            "native_run_id = 'run-1' WHERE id = ?",
            (unlinked["id"],),
        )
        activation_store.attach_consumed_activation_to_delegation(
            connection,
            event_id=str(unlinked["id"]),
            trace_id="trace",
            work_unit_id=unit,
        )
        connection.commit()
    finally:
        connection.close()
    linked = store.get_delegations("trace")[0]
    assert linked["activation_receipt_id"] == prepared["receipt_id"]


def test_expired_grant_remains_unconsumed_and_creates_no_evidence(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "expired.db")
    prepared = _prepare(store, slug, unit, ttl_seconds=1)
    time.sleep(2.0)

    with pytest.raises(ValueError, match="activation token expired"):
        _consume(store, prepared, slug, unit)

    connection = store._connect()
    try:
        grant = connection.execute(
            "SELECT consumed_at FROM delegation_activation_receipts WHERE id = ?",
            (prepared["receipt_id"],),
        ).fetchone()
        consumptions = connection.execute(
            "SELECT COUNT(*) FROM delegation_activation_consumptions"
        ).fetchone()[0]
        loads = connection.execute(
            "SELECT COUNT(*) FROM specialists_loaded WHERE trace_id = 'trace' AND agent_slug = ?",
            (slug,),
        ).fetchone()[0]
    finally:
        connection.close()
    assert grant["consumed_at"] is None
    assert consumptions == loads == 0


def test_grant_issuance_requires_the_exact_selected_version_to_remain_active(
    tmp_path: Path,
) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "inactive.db")
    store.deactivate_agent(slug)

    with pytest.raises(ValueError, match="unavailable or inactive"):
        _prepare(store, slug, unit)

    connection = store._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM delegation_activation_receipts").fetchone()[0]
            == 0
        )
    finally:
        connection.close()


def test_concurrent_consumption_has_exactly_one_winner(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "concurrent.db")
    prepared = _prepare(store, slug, unit)
    barrier = Barrier(2)

    def consume(index: int) -> tuple[str, object]:
        barrier.wait()
        try:
            return (
                "ok",
                _consume(
                    store,
                    prepared,
                    slug,
                    unit,
                    worker_id=f"worker-{index}",
                    native_run_id=f"run-{index}",
                ),
            )
        except ValueError as exc:
            return "error", str(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            future.result(timeout=10)
            for future in (executor.submit(consume, 1), executor.submit(consume, 2))
        ]

    assert sorted(status for status, _value in outcomes) == ["error", "ok"]
    assert "already consumed" in next(value for status, value in outcomes if status == "error")
    connection = store._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM delegation_activation_consumptions"
            ).fetchone()[0]
            == 1
        )
    finally:
        connection.close()


def test_prebound_grant_rejects_wrong_child_without_consuming_token(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "prebound.db")
    prepared = _prepare(store, slug, unit, worker_id="expected-worker")
    grant = deserialize_native_child_activation_grant(
        activation_store.serialize_native_child_activation_grant(prepared["activation_grant"])
    )

    assert grant.worker_binding is not None
    assert grant.worker_binding.as_dict() == {
        "mode": "prebound",
        "worker_kind": "generic-worker",
        "worker_id": "expected-worker",
    }
    with pytest.raises(ValueError, match="different worker_id"):
        _consume(store, prepared, slug, unit, worker_id="racing-worker")

    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT * FROM delegation_activation_receipts WHERE id = ?",
            (prepared["receipt_id"],),
        ).fetchone()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM delegation_activation_consumptions"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()
    assert {
        "worker_id": row["worker_id"],
        "native_run_id": row["native_run_id"],
        "consumed_at": row["consumed_at"],
    } == {
        "worker_id": "expected-worker",
        "native_run_id": "",
        "consumed_at": None,
    }
    with pytest.raises(ValueError, match="worker binding integrity"):
        activation_store._stored_public_grant({**dict(row), "worker_kind": "other-worker"})
    with pytest.raises(ValueError, match="worker binding integrity"):
        activation_store._stored_public_grant({**dict(row), "worker_id": "other-worker"})

    consumed = _consume(store, prepared, slug, unit, worker_id="expected-worker")
    assert consumed["worker_id"] == "expected-worker"


@pytest.mark.parametrize("prepared_worker", ["", "legacy-worker"], ids=["late", "prebound"])
def test_v1_grant_uses_authoritative_row_for_one_time_worker_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prepared_worker: str,
) -> None:
    store, slug, unit = _isolated_turn(tmp_path / f"v1-{prepared_worker or 'late'}.db")

    def build_v1(**arguments: object):
        arguments.pop("worker_binding", None)
        return build_native_child_activation_grant(
            **arguments,
            version=NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
        )

    monkeypatch.setattr(activation_store, "build_native_child_activation_grant", build_v1)
    prepared = _prepare(store, slug, unit, worker_id=prepared_worker)
    grant = deserialize_native_child_activation_grant(
        activation_store.serialize_native_child_activation_grant(prepared["activation_grant"])
    )
    assert grant.version == NATIVE_CHILD_ACTIVATION_LEGACY_VERSION
    assert grant.worker_binding is None

    if prepared_worker:
        with pytest.raises(ValueError, match="different worker_id"):
            _consume(store, prepared, slug, unit, worker_id="wrong-worker")
    expected_worker = prepared_worker or "late-worker"
    consumed = _consume(store, prepared, slug, unit, worker_id=expected_worker)
    assert consumed["worker_id"] == expected_worker


def test_public_activation_payloads_are_immutable_in_sqlite(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "immutable.db")
    prepared = _prepare(store, slug, unit)
    consumed = _consume(store, prepared, slug, unit)

    connection = store._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="public activation grant is immutable"):
            connection.execute(
                "UPDATE delegation_activation_receipts SET grant_payload = '{}' WHERE id = ?",
                (prepared["receipt_id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="consumption receipt is immutable"):
            connection.execute(
                "UPDATE delegation_activation_consumptions SET receipt_payload = '{}' WHERE id = ?",
                (consumed["consumption_receipt_id"],),
            )
    finally:
        connection.rollback()
        connection.close()


def test_store_contract_helpers_fail_closed_on_invalid_public_state(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        activation_store._activation_ttl(True)
    with pytest.raises(ValueError, match="between 1 and"):
        activation_store._activation_ttl(0)
    with pytest.raises(ValueError, match="must be a list"):
        activation_store._contract_items("specialist-load", field="requirements")

    store, slug, unit = _isolated_turn(tmp_path / "integrity.db")
    prepared = _prepare(store, slug, unit)
    connection = store._connect()
    try:
        row = dict(
            connection.execute(
                "SELECT * FROM delegation_activation_receipts WHERE id = ?",
                (prepared["receipt_id"],),
            ).fetchone()
        )
    finally:
        connection.close()

    legacy = {**row, "grant_id": "", "grant_payload": ""}
    with pytest.raises(ValueError, match="no authoritative TTL"):
        activation_store._stored_public_grant(legacy)
    malformed = {**row, "grant_payload": "{}"}
    with pytest.raises(ValueError, match="integrity verification"):
        activation_store._stored_public_grant(malformed)
    mismatched = {**row, "trace_id": "other-trace"}
    with pytest.raises(ValueError, match="integrity verification"):
        activation_store._stored_public_grant(mismatched)
    rebound_late = {**row, "worker_id": "premature-worker"}
    with pytest.raises(ValueError, match="rebound before consumption"):
        activation_store._stored_public_grant(rebound_late)
    rebound_run = {**row, "native_run_id": "premature-run"}
    with pytest.raises(ValueError, match="native run"):
        activation_store._stored_public_grant(rebound_run)

    activation_store.attach_consumed_activation_to_delegation(
        None,
        event_id="",
        trace_id="trace",
        work_unit_id=unit,
    )


def test_activation_policy_and_disabled_terminalization_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "policy-edges.db")
    store.create_run(
        trace_id="trace",
        session_id="session",
        host="hermes",
    )

    assert (
        store.requires_delegation_activation(
            session_id="session",
            trace_id="missing-trace",
            specialist_slug="code-reviewer",
        )
        is False
    )
    assert (
        store.requires_delegation_activation(
            session_id="session",
            trace_id="trace",
            specialist_slug="code-reviewer",
        )
        is False
    )

    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET preflight_state = 'ready' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(activation_store, "_decode_preflight_recipe", lambda *_args, **_kw: None)
        assert (
            store.requires_delegation_activation(
                session_id="session",
                trace_id="trace",
                specialist_slug="code-reviewer",
            )
            is False
        )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            activation_store,
            "_decode_preflight_recipe",
            lambda *_args, **_kw: {"delivery_mode": "direct"},
        )
        assert (
            store.requires_delegation_activation(
                session_id="session",
                trace_id="trace",
                specialist_slug="code-reviewer",
            )
            is False
        )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            activation_store,
            "_decode_preflight_recipe",
            lambda *_args, **_kw: {"delivery_mode": "isolated"},
        )
        assert (
            store.requires_delegation_activation(
                session_id="session",
                trace_id="trace",
                specialist_slug="code-reviewer",
            )
            is True
        )

    connection = store._connect()
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(activation_store, "agent_is_enabled", lambda *_args: False)
            with pytest.raises(ValueError, match="is disabled"):
                store._reject_disabled_specialist(
                    connection,
                    session_id="missing-session",
                    trace_id="missing-trace",
                    specialist_slug="code-reviewer",
                )
    finally:
        connection.close()


def test_prepare_and_consume_adversarial_edges_are_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "activation-edges.db")
    connection = store._connect()
    try:
        run = connection.execute(
            "SELECT preflight_result FROM runs WHERE session_id = 'session' AND trace_id = 'trace'"
        ).fetchone()
    finally:
        connection.close()
    recipe = activation_store._decode_preflight_recipe(
        run["preflight_result"],
        session_id="session",
        trace_id="trace",
    )
    assert recipe is not None

    with pytest.raises(ValueError, match="stable content-free identifier"):
        _prepare(store, slug, "unit with spaces")
    with pytest.raises(ValueError, match="generic-worker attribution"):
        _prepare(store, slug, unit, worker_kind="specialist-worker")

    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET preflight_state = '' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="one ready active Agency turn"):
        _prepare(store, slug, unit)
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET preflight_state = 'ready' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(activation_store, "_decode_preflight_recipe", lambda *_args, **_kw: None)
        with pytest.raises(ValueError, match="recipe could not be verified"):
            _prepare(store, slug, unit)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            activation_store,
            "_decode_preflight_recipe",
            lambda *_args, **_kw: {**recipe, "specialist_refs": []},
        )
        with pytest.raises(ValueError, match="not selected"):
            _prepare(store, slug, unit)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            activation_store,
            "_decode_preflight_recipe",
            lambda *_args, **_kw: {**recipe, "unit_agent_plan": []},
        )
        with pytest.raises(ValueError, match="selected specialist binding"):
            _prepare(store, slug, "other-unit")
    with monkeypatch.context() as scoped:
        scoped.setattr(activation_store, "content_identity_matches", lambda *_args: False)
        with pytest.raises(ValueError, match="failed integrity verification"):
            _prepare(store, slug, unit)

    prepared = _prepare(store, slug, unit)
    grant = deserialize_native_child_activation_grant(
        activation_store.serialize_native_child_activation_grant(prepared["activation_grant"])
    )
    with pytest.raises(ValueError, match="unconsumed activation grant"):
        _prepare(store, slug, unit)

    with pytest.raises(ValueError, match="activation_token is invalid"):
        store.consume_delegation_activation(
            activation_token="",
            session_id="session",
            trace_id="trace",
            specialist_slug=slug,
            work_unit_id=unit,
            worker_id="worker-1",
            native_run_id="run-1",
        )

    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET preflight_state = '' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="non-ready or terminal turn"):
        _consume(store, prepared, slug, unit)
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET preflight_state = 'ready' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="different work unit"):
        _consume(store, prepared, slug, "other-unit")

    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET host = 'hermes' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="failed integrity verification"):
        _consume(store, prepared, slug, unit)
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET host = 'codex' WHERE trace_id = 'trace'")
        connection.commit()
    finally:
        connection.close()

    connection = store._connect()
    try:
        connection.execute(
            "UPDATE delegation_activation_receipts SET specialist_version = 'missing' WHERE id = ?",
            (prepared["receipt_id"],),
        )
        connection.commit()
    finally:
        connection.close()
    with monkeypatch.context() as scoped:
        scoped.setattr(activation_store, "_stored_public_grant", lambda _row: grant)
        with pytest.raises(ValueError, match="prompt version is unavailable"):
            _consume(store, prepared, slug, unit)
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE delegation_activation_receipts SET specialist_version = ? WHERE id = ?",
            (grant.specialist.version, prepared["receipt_id"]),
        )
        original_prompt = connection.execute(
            "SELECT content FROM agent_versions WHERE agent_slug = ? AND version = ? AND hash = ?",
            (
                grant.specialist.slug,
                grant.specialist.version,
                grant.specialist.content_hash,
            ),
        ).fetchone()["content"]
        connection.execute(
            "UPDATE agent_versions SET content = ? WHERE agent_slug = ? "
            "AND version = ? AND hash = ?",
            (
                "x" * (activation_store.MAX_SPECIALIST_PROMPT_CHARS + 1),
                grant.specialist.slug,
                grant.specialist.version,
                grant.specialist.content_hash,
            ),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="prompt exceeds the exact-delivery ceiling"):
        _consume(store, prepared, slug, unit)
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE agent_versions SET content = ? WHERE agent_slug = ? "
            "AND version = ? AND hash = ?",
            (
                original_prompt,
                grant.specialist.slug,
                grant.specialist.version,
                grant.specialist.content_hash,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(activation_store, "content_identity_matches", lambda *_args: False)
        with pytest.raises(ValueError, match="prompt failed integrity verification"):
            _consume(store, prepared, slug, unit)

    with monkeypatch.context() as scoped:
        scoped.setattr(
            activation_store,
            "_consume_worker_binding",
            lambda *_args, **_kw: ("generic-worker", "impossible-worker"),
        )
        with pytest.raises(ValueError, match="already consumed"):
            _consume(store, prepared, slug, unit)
    connection = store._connect()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM delegation_activation_consumptions"
            ).fetchone()[0]
            == 0
        )
    finally:
        connection.close()

    event_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="codex",
        work_unit_id=unit,
        recommended_agent=slug,
        status="delegated",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="run-1",
    )
    consumed = _consume(store, prepared, slug, unit)
    assert consumed["delegation_event_id"] == event_id
    assert store.get_delegations("trace")[0]["activation_receipt_id"] == prepared["receipt_id"]
    with pytest.raises(ValueError, match="consumed activation receipt"):
        _prepare(store, slug, unit)


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


def test_public_delegate_reconciles_to_consumed_native_child_lineage(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "mcp-reconcile.db")
    prepared = _prepare(store, slug, unit)
    consumed = _consume(
        store,
        prepared,
        slug,
        unit,
        worker_id="native-worker",
        native_run_id="codex-agent:native-worker",
    )

    observed = handle_tool_call(
        "agency.delegate",
        {
            "session_id": "session",
            "trace_id": "trace",
            "agent": slug,
            "task": "Review the bounded failure.",
            "backend": "codex-subagent",
            "work_unit_id": unit,
            "worker_kind": "generic-worker",
            "worker_id": "task-label-that-is-not-a-worker-id",
            "native_run_id": "task-label-that-is-not-a-native-run-id",
        },
        store=store,
    )

    assert observed["status"] == "delegation observed"
    assert observed["worker_id"] == "native-worker"
    assert observed["native_run_id"] == "codex-agent:native-worker"
    [delegation] = [
        row
        for row in store.get_delegations("trace")
        if row["work_unit_id"] == unit and row["recommended_agent"] == slug
    ]
    assert delegation["executed_worker_id"] == "native-worker"
    assert delegation["native_run_id"] == "codex-agent:native-worker"
    assert delegation["activation_receipt_id"] == prepared["receipt_id"]
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    for planned in snapshot["unit_agent_plan"]:
        if planned["work_unit_id"] == unit:
            continue
        declined = handle_tool_call(
            "agency.decline_delegation",
            {
                "session_id": "session",
                "trace_id": "trace",
                "agent": planned["recommended_agent"],
                "work_unit_id": planned["work_unit_id"],
                "reason": "Not needed for this lineage-focused test.",
            },
            store=store,
        )
        assert declined["status"] == "delegation declined"
    finalized = handle_tool_call(
        "agency.finalize",
        {
            "session_id": "session",
            "trace_id": "trace",
            "draft_text": "Reconciled child work is complete.",
            "model": "task-general",
            "host": "codex",
        },
        store=store,
    )
    assert finalized["action"] == "continue"
    assert finalized["missing"] == ["evidence_verification"]
    assert consumed["consumption_receipt_id"]


def test_consumed_lineage_can_repair_one_unlinked_delegation_receipt(tmp_path: Path) -> None:
    store, slug, unit = _isolated_turn(tmp_path / "late-reconcile.db")
    prepared = _prepare(store, slug, unit)
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="mcp",
        work_unit_id=unit,
        recommended_agent=slug,
        status="delegated",
        backend="codex-subagent",
        executed_worker_kind="generic-worker",
        executed_worker_id="task-label",
        native_run_id="task-label",
    )
    _consume(
        store,
        prepared,
        slug,
        unit,
        worker_id="native-worker",
        native_run_id="codex-agent:native-worker",
    )

    observed = handle_tool_call(
        "agency.delegate",
        {
            "session_id": "session",
            "trace_id": "trace",
            "agent": slug,
            "task": "Review the bounded failure.",
            "backend": "codex-subagent",
            "work_unit_id": unit,
            "worker_kind": "generic-worker",
            "worker_id": "native-worker",
            "native_run_id": "codex-agent:native-worker",
        },
        store=store,
    )

    assert observed["status"] == "delegation observed"
    [delegation] = [
        row
        for row in store.get_delegations("trace")
        if row["work_unit_id"] == unit and row["recommended_agent"] == slug
    ]
    assert delegation["executed_worker_id"] == "native-worker"
    assert delegation["native_run_id"] == "codex-agent:native-worker"
    assert delegation["activation_receipt_id"] == prepared["receipt_id"]
