"""Focused branch coverage for SQLite and evidence store guardrails."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.roster.source_identity import SourceIdentityError
from agency_runtime.core.store import evidence as evidence_subject
from agency_runtime.core.store import roster as roster_subject
from agency_runtime.core.store import sqlite as sqlite_subject
from agency_runtime.core.store.sqlite import Store

_DIGEST = "a" * 64


class _Result:
    def __init__(
        self,
        row: Any = None,
        *,
        rows: list[Any] | None = None,
        rowcount: int = 1,
    ) -> None:
        self.row = row
        self.rows = [] if rows is None else rows
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self.row

    def fetchall(self) -> list[Any]:
        return self.rows


class _ScriptedConnection:
    def __init__(self, responses: list[_Result | Exception]) -> None:
        self.responses = list(responses)
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.row_factory: Any = None

    def execute(self, *_args: Any, **_kwargs: Any) -> _Result:
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def create_function(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_sqlite_small_decoders_and_recursive_trigger_guard() -> None:
    assert sqlite_subject._bounded_run_metadata("{") == {}
    connection = _ScriptedConnection([_Result(), _Result((0,))])
    with pytest.raises(RuntimeError, match="recursive triggers"):
        sqlite_subject._enable_recursive_triggers(connection)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "responses",
    [
        [
            _Result(),
            _Result((1,)),
            _Result((1,)),
            _Result(("bad", "text")),
        ],
        [
            _Result(),
            _Result((1,)),
            _Result(None),
            _Result(),
            _Result((0,)),
        ],
    ],
)
def test_connect_rejects_invalid_authority_key_or_secure_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[_Result],
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _ScriptedConnection(responses)
    monkeypatch.setattr(sqlite_subject.sqlite3, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.setattr(store, "_assert_storage_files_trusted", lambda: None)
    monkeypatch.setattr(store, "_database_identity", lambda: object())
    monkeypatch.setattr(store, "_require_database_identity", lambda _identity: None)
    with pytest.raises(RuntimeError):
        store._connect()
    assert connection.closed is True


@pytest.mark.parametrize(
    ("checkpoint", "update_rowcount", "message"),
    [
        ((1, 0, 0), 1, "did not complete"),
        ((0, 0, 0), 0, "state could not be completed"),
    ],
)
def test_redaction_purge_rejects_incomplete_checkpoint_or_counter_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint: tuple[int, int, int],
    update_rowcount: int,
    message: str,
) -> None:
    store = Store(tmp_path / "agency.db")

    class _PurgeConnection:
        def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
            if "wal_checkpoint" in sql:
                return _Result(checkpoint)
            if "UPDATE store_counters" in sql:
                return _Result(rowcount=update_rowcount)
            return _Result()

        def commit(self) -> None:
            return None

    monkeypatch.setattr(store, "_database_identity", lambda: object())
    monkeypatch.setattr(store, "_require_database_identity", lambda _identity: None)
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.setattr(store, "_assert_storage_files_trusted", lambda: None)
    with pytest.raises(RuntimeError, match=message):
        store._purge_redacted_storage(_PurgeConnection())  # type: ignore[arg-type]


def test_pending_retry_receipt_positive_path_closes_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _ScriptedConnection([_Result({"trace_id": "turn"})])
    monkeypatch.setattr(store, "_connect", lambda: connection)
    assert (
        store.validate_pending_retry_receipt(
            "session",
            "receipt",
            trace_id="turn",
        )
        == "turn"
    )
    assert connection.closed is True


def test_terminal_finalization_validates_pending_interaction_pair(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    common = {
        "session_id": "session",
        "trace_id": "turn",
        "host": "codex",
        "action": "finalize",
        "response_hash": _DIGEST,
        "status": "completed",
        "expected_evidence_revision": 1,
    }
    with pytest.raises(ValueError, match="pending_interaction_kind"):
        store.commit_terminal_finalization(
            **common,
            pending_interaction_kind="invalid",
        )
    with pytest.raises(ValueError, match="must be paired"):
        store.commit_terminal_finalization(
            **common,
            pending_interaction_kind="question",
        )


def test_evidence_metadata_host_and_materialization_guards() -> None:
    assert evidence_subject._bounded_metadata("{") == {}
    owner = evidence_subject.EvidenceStoreMixin()
    with pytest.raises(ValueError, match="host is required"):
        owner.ensure_host_control_materialized("")

    connection = _ScriptedConnection(
        [
            _Result(),
            _Result(None),
            _Result(),
            _Result(None),
        ]
    )
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="postcondition"):
        owner.ensure_host_control_materialized("codex")
    assert connection.rolled_back is True
    assert connection.closed is True


def test_specialist_history_deduplicates_and_empty_run_lookup_returns_none() -> None:
    owner = evidence_subject.EvidenceStoreMixin()
    connection = _ScriptedConnection(
        [_Result(rows=[{"agent_slug": "reviewer"}, {"agent_slug": "reviewer"}])]
    )
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    assert owner.get_specialists_for_session("session") == ["reviewer"]
    assert connection.closed is True
    assert owner.get_run("") is None


class _TurnStateConnection:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.rolled_back = False
        self.closed = False
        self.committed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if self.fail:
            raise RuntimeError("turn state failed")
        if sql == "BEGIN":
            return _Result()
        if "SELECT trace_id, status, metadata" in sql:
            return _Result(
                {
                    "trace_id": "prior",
                    "status": "active",
                    "metadata": "{}",
                    "preflight_result": "{}",
                }
            )
        if "roster-generation" in sql:
            return _Result({"value": 0})
        if "FROM delegation_events" in sql:
            return _Result(rows=[])
        return _Result(None)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("decode_mode", ["raise", "trivial"])
def test_turn_state_context_handles_recipe_failure_and_trivial_fallback(
    monkeypatch: pytest.MonkeyPatch,
    decode_mode: str,
) -> None:
    owner = evidence_subject.EvidenceStoreMixin()
    connection = _TurnStateConnection()
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    if decode_mode == "raise":
        monkeypatch.setattr(
            evidence_subject,
            "_decode_preflight_recipe",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("corrupt")),
        )
    else:
        monkeypatch.setattr(
            evidence_subject,
            "_decode_preflight_recipe",
            lambda *_args, **_kwargs: {"trivial": False},
        )
    context = owner.get_turn_state_context("session")
    assert context["state_known"] is True
    assert connection.committed is True
    assert connection.closed is True


def test_turn_state_context_rolls_back_database_failures() -> None:
    owner = evidence_subject.EvidenceStoreMixin()
    connection = _TurnStateConnection(fail=True)
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="turn state failed"):
        owner.get_turn_state_context("session")
    assert connection.rolled_back is True
    assert connection.closed is True


def _active_revision_rows(
    *,
    target_content: str = "Review carefully.",
    target_metadata: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    digest = sha256(target_content.encode("utf-8")).hexdigest()
    current = {
        "id": "active",
        "agent_slug": "reviewer",
        "name": "Reviewer",
        "division": "engineering",
        "description": "Reviews changes",
        "source": "test",
        "source_id": "",
        "source_version": "1.0.0",
        "version": "v1",
        "hash": digest,
        "categories": '["review"]',
        "capabilities": '["analysis"]',
        "tool_affinity": '["git"]',
        "prompt_path": "agents/reviewer.md",
        "activated_at": "2026-07-18T00:00:00Z",
    }
    metadata = serialized_revision_metadata(
        {
            **current,
            "content": target_content,
        }
    )
    revision = {
        "agent_slug": "reviewer",
        "version": "v1",
        "source_version": "1.0.0",
        "source_id": "",
        "hash": digest,
        "content": target_content,
        "metadata": metadata if target_metadata is None else target_metadata,
    }
    return current, revision


def test_roster_source_and_generation_guards_fail_closed() -> None:
    with pytest.raises(SourceIdentityError, match="stored roster source"):
        roster_subject._validated_source_rows(
            [{"url": "HTTPS://Example.Test/agents", "name": "Agents"}]
        )

    owner = roster_subject.RosterStoreMixin()
    connection = _ScriptedConnection([_Result(), _Result(None)])
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match="generation counter"):
        owner.get_routing_roster_snapshot()
    assert connection.rolled_back is True
    assert connection.closed is True


def test_versioned_prompt_rejects_invalid_and_missing_identities(tmp_path: Path) -> None:
    store = Store(tmp_path / "prompt.db")
    store._activate_prevalidated_agent(
        {
            "slug": "coverage-reviewer",
            "name": "Coverage Reviewer",
            "version": "1.0.0",
            "prompt_body": "Review carefully.",
        }
    )
    active = store.get_roster_entry("coverage-reviewer")
    assert active is not None
    digest = str(active["hash"])
    assert store.get_versioned_specialist_prompt("", "1.0.0", digest) is None
    assert store.get_versioned_specialist_prompt("coverage-reviewer", "1.0.0", "bad\x00") is None
    assert store.get_versioned_specialist_prompt("coverage-reviewer", "", digest) is None
    assert store.get_versioned_specialist_prompt("missing", "1.0.0", digest) is None


def _roster_owner_with_rows(
    rows: list[_Result],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[roster_subject.RosterStoreMixin, _ScriptedConnection]:
    owner = roster_subject.RosterStoreMixin()
    connection = _ScriptedConnection(rows)
    owner._connect = lambda: connection  # type: ignore[attr-defined]
    owner._configured_config_path = Path.cwd() / "config.yaml"  # type: ignore[attr-defined]
    owner._frozen_db_path = Path.cwd() / "agency.db"  # type: ignore[attr-defined]
    owner._database_identity = lambda: (1, 1)  # type: ignore[attr-defined]
    monkeypatch.setattr(roster_subject, "assert_store_config_binding", lambda _owner: None)
    monkeypatch.setattr(
        roster_subject,
        "assert_active_revision_projection",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        roster_subject,
        "assert_revision_activation_authority",
        lambda *_args, **_kwargs: None,
    )
    return owner, connection


def test_rollback_requires_versions_before_opening_storage() -> None:
    owner = roster_subject.RosterStoreMixin()
    with pytest.raises(ValueError, match="target and expected"):
        owner.rollback_agent_revision(
            "reviewer",
            "",
            expected_current_version="v1",
            expected_current_hash=_DIGEST,
        )


@pytest.mark.parametrize(
    ("stage", "message"),
    [
        ("active", "active agent not found"),
        ("current_revision", "active revision is missing"),
        ("target", "revision not found"),
        ("integrity", "revision integrity failed"),
        ("metadata", "predates rollback metadata"),
    ],
)
def test_rollback_rejects_missing_or_corrupt_revision_state(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    message: str,
) -> None:
    current, revision = _active_revision_rows()
    responses = [_Result(), _Result({"value": 0})]
    if stage == "active":
        responses.append(_Result(None))
    else:
        responses.append(_Result(current))
        if stage == "current_revision":
            responses.append(_Result(None))
        else:
            responses.append(_Result(revision))
            if stage == "target":
                responses.append(_Result(None))
            elif stage == "integrity":
                responses.append(_Result({**revision, "content": ""}))
            elif stage == "metadata":
                responses.append(_Result({**revision, "metadata": "{}"}))
    owner, connection = _roster_owner_with_rows(responses, monkeypatch)
    with pytest.raises(ValueError, match=message):
        owner.rollback_agent_revision(
            "reviewer",
            "v1",
            expected_current_version="v1",
            expected_current_hash=revision["hash"],
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_rollback_noop_is_rejected_before_commit(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    agent = bundled_roster()[0]
    store.activate_agent(agent)
    generation = store.get_roster_generation()

    with pytest.raises(ValueError, match="already active"):
        store.rollback_agent_revision(
            agent["slug"],
            agent["version"],
            expected_current_version=agent["version"],
            expected_current_hash=agent["hash"],
        )

    assert store.get_roster_generation() == generation
