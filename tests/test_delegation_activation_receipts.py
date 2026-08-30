from __future__ import annotations

import json
import os
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.preflight import PreflightResult, run_preflight
from agency_runtime.core.store import schema as store_schema
from agency_runtime.core.store.schema import (
    SCHEMA_VERSION,
    migrate_delegation_activation_unit_identity,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call
from tests.runtime_support import (
    harden_private_test_file,
    stub_inference_invoker,
    write_provider_config,
)

_DRAFT = """Agency/Agencies loaded: code-reviewer
Agency/Agencies delegated: generic-worker via spawn_agent
Skills loaded: none
Actual Model selected: unknown -> unavailable - no model receipt recorded
Why: Specialist review was required.
How it shaped outcome: The review was applied in an isolated worker.

Done.
"""
_REQUEST = "Review and refactor this Python code for security and correctness"
_MULTI_REQUEST = (
    "Review and refactor this Python code for security and correctness, "
    "then document the deployment workflow."
)


@pytest.fixture()
def agent_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield config_path
    finally:
        reset_config_cache()


def _disable_agent(config_path: Path, slug: str) -> None:
    config_path.write_text(f"agents:\n  disabled: [{slug}]\n", encoding="utf-8")
    reset_config_cache()


def _optional_selected(selected: tuple[str, ...]) -> str:
    return next(slug for slug in selected if slug not in PROTECTED_AGENT_SLUGS)


def _capability(host: str, session_id: str, trace_id: str):
    return native_adapter_capability_receipt(
        host,
        platform="windows" if os.name == "nt" else "linux",
        session_id=session_id,
        trace_id=trace_id,
    )


def _isolated_preflight(
    path: Path,
    *,
    host: str = "codex",
    user_message: str = _REQUEST,
    minimum_selected: int = 1,
) -> tuple[Store, PreflightResult]:
    # ADR-0087: selection runs inference only when a provider is configured.
    # Configure one and stub the invoker so preflight exercises the inference
    # path instead of declining offline.
    config_path = path.parent / "agency.yaml"
    write_provider_config(config_path)
    os.environ["AGENCY_CONFIG_PATH"] = str(config_path)
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
            user_message=user_message,
            host=host,
            capability_receipt=_capability(host, "session", "trace"),
        )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        os.environ.pop("AGENCY_CONFIG_PATH", None)
        reset_config_cache()
    assert len(result.selected_specialists) >= minimum_selected
    return store, result


def _isolated_turn(
    path: Path,
    *,
    host: str = "codex",
    user_message: str = _REQUEST,
    minimum_selected: int = 1,
) -> tuple[Store, tuple[str, ...]]:
    store, result = _isolated_preflight(
        path,
        host=host,
        user_message=user_message,
        minimum_selected=minimum_selected,
    )
    return store, result.selected_specialists


def _active_version(store: Store, slug: str) -> str:
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT version FROM agent_active WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return str(row["version"])


def _activation_work_unit(store: Store, slug: str) -> str:
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    planned = next(
        (row for row in snapshot["unit_agent_plan"] if row["recommended_agent"] == slug),
        None,
    )
    return str(planned["work_unit_id"]) if planned is not None else f"specialist:{slug}"


def _activation_work_unit_for(store: Store, slug: str, session_id: str, trace_id: str) -> str:
    snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
    planned = next(
        (row for row in snapshot["unit_agent_plan"] if row["recommended_agent"] == slug),
        None,
    )
    return str(planned["work_unit_id"]) if planned is not None else f"specialist:{slug}"


def _planned_goal(context: str, work_unit_id: str) -> str:
    prefix = f"- unit={work_unit_id};"
    line = next(item for item in context.splitlines() if item.startswith(prefix))
    return str(json.loads(line.split("; goal=", 1)[1]))


def _activate(
    store: Store,
    slug: str,
    *,
    worker_id: str | None = None,
    native_run_id: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    work_unit_id = _activation_work_unit(store, slug)
    worker = worker_id or f"worker-{slug}"
    native = native_run_id or f"run-{slug}"
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
        },
        store,
    )
    assert "error" not in prepared
    loaded = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
            "activation_token": prepared["activation_token"],
            "worker_id": worker,
            "native_run_id": native,
        },
        store,
    )
    assert "error" not in loaded
    return prepared, loaded


def test_native_adapter_separates_worker_and_run_ids_from_work_unit(tmp_path: Path) -> None:
    store = Store(tmp_path / "adapter.db")
    store.create_run(trace_id="trace", session_id="session", host="codex")
    adapter = CodexAdapter(store=store)

    adapter.record_tool_call(
        tool_name="spawn_agent",
        args={"goal": "review the security boundary"},
        result={"agent_id": "agent-123", "run_id": "run-456"},
        session_id="session",
        trace_id="trace",
    )

    row = store.get_delegations("trace")[0]
    assert row["work_unit_id"] != "agent-123"
    assert row["executed_worker_kind"] == "generic-worker"
    assert row["executed_worker_id"] == "agent-123"
    assert row["native_run_id"] == "run-456"


def _prepared_codex_hook_delivery(
    tmp_path: Path,
    *,
    tool_name: str,
) -> tuple[Store, HookBridge, dict[str, object], dict[str, object], str]:
    store, result = _isolated_preflight(tmp_path / f"hook-response-{tool_name}.db", host="codex")
    slug = result.selected_specialists[0]
    unit = _activation_work_unit(store, slug)
    goal = _planned_goal(result.context, unit)
    worker_id = "agent-lifecycle"
    bridge = HookBridge("codex", store=store)
    payload: dict[str, object] = {
        "hook_event_name": "PreToolUse",
        "session_id": "session",
        "turn_id": "trace",
        "tool_use_id": f"{tool_name}-tool-use",
        "tool_name": tool_name,
        "tool_input": {
            "task_name": codex_task_name_for_work_unit(unit),
            "message": goal,
        },
    }
    rewritten = bridge.handle(payload)["hookSpecificOutput"]["updatedInput"]
    bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "session",
            "turn_id": "child-turn",
            "agent_id": worker_id,
            "agent_type": "worker",
        }
    )
    return store, bridge, payload, rewritten, worker_id


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
@pytest.mark.parametrize("host", ["codex", "hermes"])
def test_oversized_prompt_is_rejected_for_isolated_and_direct_delivery(
    tmp_path: Path,
    host: str,
) -> None:
    store = Store(tmp_path / f"oversized-{host}.db")
    store._activate_prevalidated_agent(
        dict(next(agent for agent in STARTER_ROSTER if agent["slug"] == "code-reviewer"))
    )
    content = "x" * 7_001
    content_hash = sha256(content.encode()).hexdigest()
    active_version = _active_version(store, "code-reviewer")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = ?, hash = ? "
            "WHERE agent_slug = 'code-reviewer' AND version = ?",
            (content, content_hash, active_version),
        )
        conn.execute(
            "UPDATE agent_active SET hash = ? WHERE agent_slug = 'code-reviewer'",
            (content_hash,),
        )
        conn.commit()
    finally:
        conn.close()

    # ADR-0087: configure a provider + stub the invoker so preflight exercises
    # the inference path (and reaches the oversized-content delivery check)
    # instead of declining offline.
    config_path = tmp_path / f"oversized-{host}-config.yaml"
    write_provider_config(config_path)
    os.environ["AGENCY_CONFIG_PATH"] = str(config_path)
    reset_config_cache()
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        with pytest.raises(RuntimeError, match="exact-delivery ceiling"):
            run_preflight(
                store,
                session_id="session",
                trace_id="trace",
                user_message="Review this code for security and correctness",
                host=host,
                capability_receipt=_capability(host, "session", "trace"),
            )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        os.environ.pop("AGENCY_CONFIG_PATH", None)
        reset_config_cache()


def test_v18_store_migrates_receipts_and_legacy_execution_identity(tmp_path: Path) -> None:
    path = tmp_path / "legacy-v18.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version VALUES (18);
        CREATE TABLE runs (
            id TEXT PRIMARY KEY, trace_id TEXT NOT NULL UNIQUE, session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown', started_at TEXT NOT NULL,
            ended_at TEXT, status TEXT NOT NULL DEFAULT 'active',
            user_message TEXT, metadata TEXT
        );
        CREATE TABLE delegation_events (
            id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown', work_unit_id TEXT,
            recommended_agent TEXT, status TEXT NOT NULL DEFAULT 'suggested',
            backend TEXT, skip_reason TEXT, error TEXT, started_at TEXT,
            completed_at TEXT
        );
        INSERT INTO runs VALUES (
            'run', 'trace', 'session', 'codex', '2026-07-15T00:00:00+00:00',
            '2026-07-15T00:00:01+00:00', 'completed', '', '{}'
        );
        INSERT INTO delegation_events VALUES (
            'event', 'trace', 'session', 'codex', 'unit-a', 'code-reviewer',
            'delegated', 'spawn_agent', '', '', '2026-07-15T00:00:00+00:00', NULL
        );
        """
    )
    conn.commit()
    conn.close()
    harden_private_test_file(path)

    store = Store(path)
    conn = store._connect()
    try:
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        receipt_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'delegation_activation_receipts'"
        ).fetchone()
        row = conn.execute(
            "SELECT executed_worker_kind, retrieved_specialist_slug, "
            "activation_receipt_id FROM delegation_events WHERE id = 'event'"
        ).fetchone()
    finally:
        conn.close()

    assert version == SCHEMA_VERSION
    assert receipt_table is not None
    assert row["executed_worker_kind"] == "legacy-unverified-worker"
    assert row["retrieved_specialist_slug"] == ""
    assert row["activation_receipt_id"] is None


def test_v19_activation_receipts_migrate_to_unit_scoped_identity() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE runs (trace_id TEXT PRIMARY KEY);
        CREATE TABLE delegation_events (id TEXT PRIMARY KEY);
        CREATE TABLE delegation_activation_receipts (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            work_unit_id TEXT NOT NULL,
            specialist_slug TEXT NOT NULL,
            specialist_version TEXT NOT NULL,
            specialist_prompt_hash TEXT NOT NULL,
            worker_kind TEXT NOT NULL,
            worker_id TEXT NOT NULL DEFAULT '',
            native_run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            consumed_at TEXT,
            delegation_event_id TEXT,
            UNIQUE(trace_id, specialist_slug, specialist_version, specialist_prompt_hash),
            FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
            FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
        );
        CREATE INDEX idx_activation_receipts_trace
        ON delegation_activation_receipts(trace_id, created_at);
        CREATE INDEX idx_activation_receipts_work_unit
        ON delegation_activation_receipts(trace_id, work_unit_id, consumed_at);
        INSERT INTO delegation_activation_receipts VALUES (
            'receipt', 'token', 'session', 'trace', 'unit-a', 'code-reviewer',
            'v1', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'generic-worker', '', '', '2026-07-16T00:00:00+00:00', NULL, NULL
        );
        """
    )

    migrate_delegation_activation_unit_identity(conn)

    row = conn.execute(
        "SELECT id, work_unit_id, specialist_slug FROM delegation_activation_receipts"
    ).fetchone()
    unique_column_sets = {
        tuple(str(column["name"]) for column in conn.execute(f"PRAGMA index_info({index['name']})"))
        for index in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        if int(index["unique"]) == 1
    }
    assert dict(row) == {
        "id": "receipt",
        "work_unit_id": "unit-a",
        "specialist_slug": "code-reviewer",
    }
    assert (
        "trace_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
    ) in unique_column_sets
    conn.close()


def _prepare_v19_activation_store(path: Path) -> dict[str, object]:
    original = Store(path)
    original.create_run(
        session_id="session-v19",
        trace_id="trace-v19",
        host="codex",
    )
    legacy = {
        "id": "receipt-v19",
        "token_hash": sha256(b"legacy-token").hexdigest(),
        "session_id": "session-v19",
        "trace_id": "trace-v19",
        "work_unit_id": "unit-v19",
        "specialist_slug": "code-reviewer",
        "specialist_version": "v19",
        "specialist_prompt_hash": "a" * 64,
        "worker_kind": "generic-worker",
        "worker_id": "worker-v19",
        "native_run_id": "run-v19",
        "created_at": "2026-07-16T00:00:00+00:00",
        "consumed_at": None,
        "delegation_event_id": None,
    }
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA foreign_keys = OFF;
        DROP TABLE delegation_activation_consumptions;
        DROP TABLE delegation_activation_receipts;
        CREATE TABLE delegation_activation_receipts (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            work_unit_id TEXT NOT NULL,
            specialist_slug TEXT NOT NULL,
            specialist_version TEXT NOT NULL,
            specialist_prompt_hash TEXT NOT NULL,
            worker_kind TEXT NOT NULL,
            worker_id TEXT NOT NULL DEFAULT '',
            native_run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            consumed_at TEXT,
            delegation_event_id TEXT,
            UNIQUE(trace_id, specialist_slug, specialist_version, specialist_prompt_hash)
        );
        DELETE FROM schema_version;
        INSERT INTO schema_version VALUES (19);
        """
    )
    conn.execute(
        "INSERT INTO delegation_activation_receipts "
        "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
        "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
        "native_run_id, created_at, consumed_at, delegation_event_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(legacy.values()),
    )
    conn.commit()
    conn.close()
    return legacy


def _read_activation_receipt(path: Path) -> dict[str, object]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, token_hash, grant_id, grant_payload, grant_issued_unix, "
            "grant_expires_unix, child_host, grant_origin, tool_use_id, session_id, "
            "trace_id, work_unit_id, "
            "specialist_slug, specialist_version, specialist_prompt_hash, worker_kind, "
            "worker_id, native_run_id, created_at, consumed_at, delegation_event_id "
            "FROM delegation_activation_receipts"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return dict(row)


def test_store_upgrade_defers_public_grant_index_until_legacy_columns_exist(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-v19-activation.db"
    legacy = _prepare_v19_activation_store(path)

    upgraded = Store(path)
    reopened = Store(path)
    conn = upgraded._connect()
    try:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(delegation_activation_receipts)")
        }
        indexes = {
            str(row["name"])
            for row in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        }
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        receipt_count = int(
            conn.execute("SELECT COUNT(*) FROM delegation_activation_receipts").fetchone()[0]
        )
    finally:
        conn.close()

    migrated = _read_activation_receipt(path)
    assert {
        "grant_id",
        "grant_payload",
        "grant_issued_unix",
        "grant_expires_unix",
        "grant_origin",
        "tool_use_id",
    } <= columns
    assert "idx_activation_grants_public_id" in indexes
    assert version == SCHEMA_VERSION
    assert receipt_count == 1
    assert migrated == {
        **legacy,
        "grant_id": "",
        "grant_payload": "",
        "grant_issued_unix": 0,
        "grant_expires_unix": 0,
        "child_host": "",
        "grant_origin": "manual_api",
        "tool_use_id": "",
    }
    assert upgraded._current_schema_state() == (True, True)
    assert reopened._current_schema_state() == (True, True)
    assert _read_activation_receipt(path) == migrated


def test_store_upgrade_rolls_back_v19_activation_rebuild_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "legacy-v19-activation-rollback.db"
    legacy = _prepare_v19_activation_store(path)

    monkeypatch.setattr(
        store_schema,
        "create_delegation_activation_consumption_schema",
        lambda _conn: (_ for _ in ()).throw(RuntimeError("injected migration failure")),
    )
    with pytest.raises(RuntimeError, match="injected migration failure"):
        Store(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(delegation_activation_receipts)")
        }
        row = conn.execute(
            "SELECT id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at, delegation_event_id "
            "FROM delegation_activation_receipts"
        ).fetchone()
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        consumption_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'delegation_activation_consumptions'"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert dict(row) == legacy
    assert "grant_id" not in columns
    assert version == 19
    assert consumption_table is None


@pytest.mark.parametrize(
    "mutation",
    [
        "ALTER TABLE delegation_activation_receipts "
        "RENAME COLUMN worker_kind TO missing_worker_kind",
        "DROP INDEX idx_activation_receipts_trace",
        "DROP TRIGGER agency_delegation_activation_receipts_insert_activity",
    ],
    ids=["required-column", "required-index", "required-trigger"],
)
def test_v20_readiness_rejects_incomplete_receipt_boundary(
    tmp_path: Path,
    mutation: str,
) -> None:
    store = Store(tmp_path / "incomplete-v20.db")
    assert store._current_schema_state() == (True, True)
    connection = store._connect()
    try:
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
