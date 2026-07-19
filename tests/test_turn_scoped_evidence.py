"""Turn-scoped evidence lifecycle and host-correlation regressions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.delegation.events import work_unit_id_from_text
from agency_runtime.core.header.contract import (
    EvidenceCorrelationError,
    fill_header_fields,
    format_header,
)
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.specialist_context import (
    hydrate_selected_specialist_context,
)
from agency_runtime.core.store.schema import SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call


def test_v11_migration_preserves_uncorrelated_rows_as_history_only(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (10);
        CREATE TABLE specialists_loaded (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent_slug TEXT NOT NULL,
            loaded_at TEXT NOT NULL
        );
        CREATE TABLE skills_loaded (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            loaded_at TEXT NOT NULL
        );
        INSERT INTO specialists_loaded VALUES
            ('specialist-1', 'session-1', 'reviewer', '2026-07-01T00:00:00Z');
        INSERT INTO skills_loaded VALUES
            ('skill-1', 'session-1', 'security', '2026-07-01T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()

    store = Store(db_path)

    assert store.get_specialists_for_session("session-1") == ["reviewer"]
    assert store.get_active_specialists_for_trace("session-1", "turn-1") == []
    assert store.get_skills_for_session("session-1") == ["security"]
    assert store.get_skills_for_trace("session-1", "turn-1") == []
    [history] = store.get_specialist_load_history("session-1")
    assert history["trace_id"] == ""
    assert history["expired_at"] == history["loaded_at"]
    conn = store._connect()
    try:
        assert (
            conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == SCHEMA_VERSION
        )
    finally:
        conn.close()


def test_header_reads_only_one_trace_and_history_survives_close(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session", "turn-one-agent", trace_id="turn-1")
    store.record_skill_loaded("session", "turn-one-skill", trace_id="turn-1")
    store.record_delegation(
        trace_id="turn-1",
        session_id="session",
        work_unit_id="unit-1",
        recommended_agent="turn-one-agent",
        status="delegated",
        backend="delegate_task",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )
    store.record_model_receipt(
        trace_id="turn-1",
        session_id="session",
        requested_model="task-general",
        resolved_provider="provider-one",
        resolved_model="model-one",
    )
    store.record_specialist_loaded("session", "turn-two-agent", trace_id="turn-2")
    store.record_skill_loaded("session", "turn-two-skill", trace_id="turn-2")
    store.record_model_receipt(
        trace_id="turn-2",
        session_id="session",
        requested_model="task-general",
        resolved_provider="provider-two",
        resolved_model="model-two",
    )

    fields = fill_header_fields({}, "session", store, "task-general", "turn-2")

    assert fields["agencies_loaded"] == "turn-two-agent"
    assert fields["skills_loaded"] == "turn-two-skill"
    assert fields["agencies_delegated"] == "none"
    assert "provider-two/model-two" in fields["actual_model_selected"]
    assert "turn-one" not in " ".join(fields.values())
    store.close_turn_evidence("session", "turn-2")
    assert store.get_active_specialists_for_trace("session", "turn-2") == []
    assert store.get_specialists_for_trace("session", "turn-2") == ["turn-two-agent"]
    snapshot = store.get_completion_evidence_snapshot("session", "turn-2")
    assert snapshot["specialists"] == ["turn-two-agent"]
    with pytest.raises(EvidenceCorrelationError, match="terminal Agency turn"):
        fill_header_fields({}, "session", store, "task-general", "turn-2")


def test_finalize_fails_closed_without_correlation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    result = finalize_response(
        "Substantive answer.",
        trace_metadata={"session_id": "session"},
        store=store,
    )

    assert result == {
        "action": "continue",
        "text": "Substantive answer.",
        "missing": ["trace_id"],
    }
    assert "Agency/Agencies loaded: none" not in result["text"]


def test_closed_trace_is_read_only_and_cannot_be_reopened(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    run_id = store.create_run(trace_id="turn", session_id="session", host="test")
    assert store.create_run(trace_id="turn", session_id="session", host="test") == run_id
    store.record_specialist_loaded("session", "reviewer", trace_id="turn")
    store.close_turn_evidence("session", "turn")

    with pytest.raises(ValueError, match="terminal"):
        store.create_run(trace_id="turn", session_id="session", host="test")
    with pytest.raises(ValueError, match="terminal"):
        store.record_specialist_loaded("session", "new-agent", trace_id="turn")
    with pytest.raises(ValueError, match="terminal"):
        store.record_skill_loaded("session", "new-skill", trace_id="turn")
    with pytest.raises(ValueError, match="terminal"):
        store.record_delegation(
            trace_id="turn",
            session_id="session",
            work_unit_id="new-unit",
            status="delegated",
        )

    replay = finalize_response(
        "Answer.",
        trace_metadata={"session_id": "session", "trace_id": "turn"},
        store=store,
    )
    assert replay == {
        "action": "continue",
        "text": "Answer.",
        "missing": ["correlation"],
    }
    assert store.get_completion_evidence_snapshot("session", "turn")["specialists"] == ["reviewer"]
    with pytest.raises(EvidenceCorrelationError, match="terminal Agency turn"):
        fill_header_fields({}, "session", store, trace_id="turn")
    with pytest.raises(ValueError, match="different session"):
        store.create_run(trace_id="other", session_id="first")
        store.create_run(trace_id="other", session_id="second")


def test_header_finalize_then_claude_stop_recovers_and_closes_turn(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host="mcp",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("session", "reviewer", trace_id="turn")
    finalized = finalize_response(
        "Answer.",
        trace_metadata={
            "session_id": "session",
            "trace_id": "turn",
            "host": "mcp",
        },
        store=store,
        model="task-general",
    )
    assert finalized["action"] == "accept"
    assert store.get_run("turn")["status"] == "completed"
    assert store.get_active_specialists_for_trace("session", "turn") == []
    replayed = finalize_response(
        finalized["text"],
        trace_metadata={
            "session_id": "session",
            "trace_id": "turn",
            "host": "mcp",
        },
        store=store,
        model="task-general",
    )
    assert replayed == finalized
    assert [
        row["action"]
        for row in store.recent_runtime_activity()["finalizations"]
        if row["trace_id"] == "turn"
    ] == ["accept"]

    stopped = HookBridge("claude", store=store).handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session",
            "model": "task-general",
            "stop_hook_active": False,
            "last_assistant_message": finalized["text"],
        }
    )

    assert stopped == {}
    assert store.get_run("turn")["status"] == "completed"
    assert store.get_active_specialists_for_trace("session", "turn") == []
    assert store.get_specialists_for_trace("session", "turn") == ["reviewer"]


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_mcp_finalize_then_native_stop_idempotently_accepts_exact_text(
    host: str,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    preflight = handle_tool_call(
        "agency.preflight",
        {
            "session_id": "session",
            "trace_id": "turn",
            "host": host,
            "user_message": "Thanks.",
        },
        store=store,
    )
    assert preflight["trace_id"] == "turn"
    assert preflight["selected_specialists"] == []
    finalized = handle_tool_call(
        "agency.finalize",
        {
            "session_id": "session",
            "trace_id": "turn",
            "draft_text": "You're welcome.",
            "model": "task-general",
        },
        store=store,
    )
    assert finalized["action"] == "accept"
    completed = store.get_run("turn")
    assert completed is not None
    assert completed["status"] == "completed"
    ended_at = completed["ended_at"]
    bridge = HookBridge(host, store=store)
    payload = {
        "hook_event_name": "Stop",
        "session_id": "session",
        "turn_id": "turn",
        "last_assistant_message": finalized["text"],
    }

    assert bridge.handle(payload) == {}
    after_exact = store.get_run("turn")
    assert after_exact is not None
    assert after_exact["status"] == "completed"
    assert after_exact["ended_at"] == ended_at
    actions = [
        row for row in store.recent_runtime_activity()["finalizations"] if row["trace_id"] == "turn"
    ]
    assert [row["action"] for row in actions] == ["accept"]

    altered = bridge.handle(
        {
            **payload,
            "last_assistant_message": finalized["text"] + "\nAltered.",
        }
    )
    assert altered["continue"] is False
    assert "does not match the exact response" in altered["stopReason"]


def test_public_delegate_and_post_tool_hook_record_one_execution(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    run_preflight(
        store,
        session_id="session",
        trace_id="turn",
        user_message="Review authentication and report the result.",
        host="codex",
    )
    arguments = {
        "agent": "reviewer",
        "task": "Review authentication",
        "backend": "spawn_agent",
        "trace_id": "turn",
        "session_id": "session",
        "work_unit_id": "unit-auth",
        "worker_kind": "generic-worker",
        "worker_id": "worker-1",
        "native_run_id": "native-run-1",
    }

    observed = handle_tool_call("agency.delegate", arguments, store=store)
    assert observed["status"] == "delegation observed"
    HookBridge("codex", store=store).handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session",
            "turn_id": "turn",
            "tool_use_id": "tool-1",
            "tool_name": "mcp__agency__agency.delegate",
            "tool_input": arguments,
            "tool_response": observed,
        }
    )

    [delegation] = store.get_delegations("turn")
    assert delegation["status"] == "delegated"
    assert delegation["backend"] == "spawn_agent"
    assert delegation["work_unit_id"] == "unit-auth"

    before = len(store.get_delegations("turn"))
    rejected = handle_tool_call(
        "agency.delegate",
        {**arguments, "trace_id": "turn", "work_unit_id": ""},
        store=store,
    )
    assert "non-empty work_unit_id" in rejected["error"]
    assert len(store.get_delegations("turn")) == before


def test_native_spawn_agent_preserves_backend_without_inventing_specialist_identity(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="turn", session_id="session", host="codex")

    HookBridge("codex", store=store).handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session",
            "turn_id": "turn",
            "tool_use_id": "tool-1",
            "tool_name": "functions.collaboration.spawn_agent",
            "tool_input": {
                "task_name": "review_auth",
                "message": "Review authentication",
            },
            "tool_response": {"agent_id": "worker-1"},
        }
    )

    [delegation] = store.get_delegations("turn")
    assert delegation["recommended_agent"] == ""
    assert delegation["backend"] == "spawn_agent"
    assert delegation["work_unit_id"] == work_unit_id_from_text("Review authentication")
    assert delegation["executed_worker_kind"] == "generic-worker"
    assert delegation["executed_worker_id"] == "worker-1"


@pytest.mark.parametrize("host", ["claude", "codex"])
def test_stop_retry_terminally_stops_both_native_hosts_without_loop(
    host: str,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host=host,
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("session", "reviewer", trace_id="turn")
    bridge = HookBridge(host, store=store)
    payload = {
        "hook_event_name": "Stop",
        "session_id": "session",
        "turn_id": "turn",
        "last_assistant_message": "Missing header.",
    }

    # Codex may omit stop_hook_active. The durable prior continue action is the
    # retry authority for both native hosts.
    first = bridge.handle(payload)
    terminal = bridge.handle(payload)
    exact_replay = bridge.handle(payload)

    assert first["decision"] == "block"
    assert set(terminal) == {"continue", "stopReason"}
    assert terminal["continue"] is False
    assert terminal["stopReason"].startswith("AGENCY RETRY EXHAUSTED:")
    assert "No further correction is requested" in terminal["stopReason"]
    assert exact_replay == terminal
    without_turn_id = bridge.handle(
        {key: value for key, value in payload.items() if key != "turn_id"}
    )
    assert without_turn_id == terminal
    altered = bridge.handle({**payload, "last_assistant_message": "Different response."})
    assert altered["continue"] is False
    assert altered["stopReason"].startswith("AGENCY TURN TERMINAL:")
    assert "Re-run Agency preflight" not in altered["stopReason"]
    assert store.get_run("turn")["status"] == "retry_exhausted"
    assert store.get_active_specialists_for_trace("session", "turn") == []
    actions = [row["action"] for row in store.recent_runtime_activity()["finalizations"]]
    assert "continue" in actions
    assert "retry_exhausted" in actions


def test_pre_verify_rejects_terminal_trace_but_history_remains_readable(
    tmp_path: Path,
) -> None:
    from agency_runtime.adapters.hermes.plugin import HermesAdapter

    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        metadata={"request_kind": "trivial"},
    )
    store.record_specialist_loaded("session", "reviewer", trace_id="turn")
    fields = fill_header_fields(
        {
            "why": "A review was requested.",
            "how_it_shaped_outcome": "The reviewer shaped the response.",
        },
        "session",
        store,
        trace_id="turn",
    )
    response = f"{format_header(fields)}\n\nReviewed."
    store.close_turn_evidence("session", "turn")

    decision = HermesAdapter(store=store).pre_verify_handler(
        response,
        session_id="session",
        trace_id="turn",
    )

    assert decision is not None
    assert decision["action"] == "continue"
    assert "AGENCY TURN TERMINAL" in decision["message"]
    assert "Re-run Agency preflight" not in decision["message"]
    assert store.get_completion_evidence_snapshot("session", "turn")["specialists"] == ["reviewer"]
    with pytest.raises(EvidenceCorrelationError, match="terminal Agency turn"):
        fill_header_fields({}, "session", store, trace_id="turn")


def test_pre_verify_store_exception_requires_revision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.adapters.hermes.plugin import HermesAdapter

    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        metadata={"request_kind": "trivial"},
    )
    fields = fill_header_fields(
        {
            "why": "Turn-scoped evidence was checked.",
            "how_it_shaped_outcome": "The response remained evidence based.",
        },
        "session",
        store,
        trace_id="turn",
    )
    response = f"{format_header(fields)}\n\nComplete."
    monkeypatch.setattr(
        store,
        "get_completion_evidence_snapshot",
        lambda *_args: (_ for _ in ()).throw(OSError("database offline")),
    )

    decision = HermesAdapter(store=store).pre_verify_handler(
        response,
        session_id="session",
        trace_id="turn",
    )

    assert decision is not None
    assert decision["action"] == "continue"
    assert "VERIFICATION UNAVAILABLE" in decision["message"]


class _PromptStore:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, str, str]] = []

    def get_specialist_prompt(self, slug: str, *, max_chars: int) -> dict[str, Any]:
        return {
            "agent_slug": slug,
            "description": slug,
            "prompt_body": "x" * max_chars,
            "version": "1.0.0",
            "prompt_hash": "a" * 64,
        }

    def record_specialist_loaded(
        self,
        session_id: str,
        slug: str,
        *,
        trace_id: str,
    ) -> None:
        self.loaded.append((session_id, trace_id, slug))


def test_selected_specialist_context_has_count_and_aggregate_budgets() -> None:
    store = _PromptStore()
    catalog = [{"slug": f"agent-{index}"} for index in range(5)]
    loaded = hydrate_selected_specialist_context(
        store,  # type: ignore[arg-type]
        catalog,
        {"selected_ids": [row["slug"] for row in catalog]},
        session_id="session",
        trace_id="turn",
    )

    assert len(loaded.slugs) == 3
    assert len(loaded.context) <= 24_000
    assert store.loaded == [
        ("session", "turn", "agent-0"),
        ("session", "turn", "agent-1"),
        ("session", "turn", "agent-2"),
    ]
