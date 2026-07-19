"""Branch-complete tests for turn identity and Store boundary helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import correlation
from agency_runtime.core.store import queries, trace_identity
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.version_identity import (
    MAX_VERSION_IDENTITY_BYTES,
    is_valid_version_identity,
    normalize_version_identity,
)
from agency_runtime.core.turn_correlation import active_turn_error


class _BrokenUtf8(str):
    """Exercise the defensive encode failure after printable validation."""

    def strip(self, chars: str | None = None) -> _BrokenUtf8:
        del chars
        return self

    def isprintable(self) -> bool:
        return True

    def encode(self, *_args: Any, **_kwargs: Any) -> bytes:
        raise UnicodeEncodeError("utf-8", self, 0, 1, "synthetic encoding failure")


def test_correlation_validator_translates_utf8_encoding_failures() -> None:
    with pytest.raises(ValueError, match="valid UTF-8 text"):
        correlation.validate_correlation_id(_BrokenUtf8("x"), field="trace_id")


def _identity_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE store_secrets ("
        "name TEXT PRIMARY KEY, secret BLOB NOT NULL, created_at TEXT NOT NULL)"
    )
    return conn


def test_trace_identity_integrity_fails_closed_and_can_initialize_verifier() -> None:
    conn = _identity_connection()
    try:
        key = b"k" * 32
        conn.execute(
            "INSERT INTO store_secrets VALUES (?, ?, 'now')",
            ("retired-trace-hmac-v1", key),
        )
        with pytest.raises(RuntimeError, match="verifier is unavailable"):
            trace_identity.ensure_correlation_key_integrity(conn, allow_initialize=False)

        assert trace_identity.ensure_correlation_key_integrity(conn, allow_initialize=True) == key
        assert trace_identity.correlation_digest(conn, "turn", domain="trace")
        trace_digest, session_digest = trace_identity.correlation_pair_digests(
            conn,
            trace_id="turn",
            session_id="",
        )
        assert len(trace_digest) == len(session_digest) == 64

        conn.execute(
            "UPDATE store_secrets SET secret = ? WHERE name = ?",
            (b"x" * 32, "retired-trace-hmac-v1-verifier"),
        )
        with pytest.raises(RuntimeError, match="does not match"):
            trace_identity.ensure_correlation_key_integrity(conn, allow_initialize=False)

        conn.execute("DELETE FROM store_secrets")
        with pytest.raises(RuntimeError, match="key is unavailable"):
            trace_identity.ensure_correlation_key_integrity(conn, allow_initialize=False)
        conn.execute(
            "INSERT INTO store_secrets VALUES (?, ?, 'now')",
            ("retired-trace-hmac-v1", b"short"),
        )
        with pytest.raises(RuntimeError, match="key is invalid"):
            trace_identity.ensure_correlation_key_integrity(conn, allow_initialize=False)
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("value", "domain"),
    [("", "trace"), ("turn", "unknown")],
)
def test_trace_identity_rejects_unsupported_digest_inputs(value: str, domain: str) -> None:
    with pytest.raises(ValueError, match="supported digest domain"):
        trace_identity._digest_with_key(b"k" * 32, value, domain=domain)


def test_version_identity_fallback_and_rejection_paths() -> None:
    generated = normalize_version_identity(None, fallback_content="prompt")
    assert len(generated) == 64
    assert is_valid_version_identity("opaque-v1") is True
    assert is_valid_version_identity("") is False
    for value in ("x" * (MAX_VERSION_IDENTITY_BYTES + 1), "bad\x7fidentity"):
        with pytest.raises(ValueError, match="bounded opaque identifier"):
            normalize_version_identity(value)


class _TurnStore:
    def __init__(self, result: Any = None, *, raises: bool = False) -> None:
        self.result = result
        self.raises = raises

    def get_run(self, _trace_id: str) -> Any:
        if self.raises:
            raise RuntimeError("read failed")
        return self.result


@pytest.mark.parametrize(
    ("store", "session_id", "trace_id", "expected"),
    [
        (object(), "session", "turn", "could not be verified"),
        (_TurnStore(raises=True), "session", "turn", "could not be verified"),
        (_TurnStore(None), "session", "turn", "does not identify"),
        (
            _TurnStore({"session_id": "other", "status": "active", "ended_at": None}),
            "session",
            "turn",
            "different session",
        ),
        (
            _TurnStore({"session_id": "session", "status": "completed", "ended_at": "now"}),
            "session",
            "turn",
            "terminal turn",
        ),
        (
            _TurnStore({"session_id": "session", "status": "active", "ended_at": "now"}),
            "session",
            "turn",
            "terminal turn",
        ),
        (
            _TurnStore({"session_id": "session", "status": "evidence_only", "ended_at": None}),
            "session",
            "turn",
            "not completed preflight",
        ),
        (
            _TurnStore(
                {
                    "session_id": "session",
                    "status": "active",
                    "ended_at": None,
                    "preflight_state": "in_progress",
                }
            ),
            "session",
            "turn",
            "not completed preflight",
        ),
        (
            _TurnStore(
                {
                    "session_id": "session",
                    "status": "active",
                    "ended_at": None,
                    "preflight_state": "ready",
                }
            ),
            "session",
            "turn",
            "",
        ),
    ],
)
def test_active_turn_error_covers_verification_boundaries(
    store: object,
    session_id: str,
    trace_id: str,
    expected: str,
) -> None:
    assert expected in active_turn_error(store, session_id, trace_id)


def test_active_turn_error_reports_invalid_public_correlation() -> None:
    assert active_turn_error(_TurnStore({}), "", "turn") == "session_id is required"


def test_routing_projection_bounds_invalid_scalars_and_all_sources() -> None:
    assert queries._bounded_routing_list("not-a-list") == []
    assert queries._bounded_routing_list(["one", "two"]) == ["one", "two"]
    assert queries._bounded_routing_list(["one", "one", ""]) == ["one"]
    assert queries._bounded_routing_float(object()) == 0.0
    assert queries._bounded_routing_float(float("inf")) == 0.0
    assert queries._bounded_routing_count(True) == 0
    assert queries._bounded_routing_count(object()) == 0
    assert queries._project_routing_field("provider", " provider ") == "provider"
    assert queries._project_routing_field("trace_id", " turn ") == "turn"
    assert queries._project_routing_field("unknown", "value") is queries._OMIT_ROUTING_FIELD

    for decision, expected in (
        ({"cache_hit": True}, "cache"),
        ({"session_reused": True}, "session"),
        ({"source": "policy_fallback"}, "policy_fallback"),
        ({}, "computed"),
    ):
        _safe, _work_units, source = queries.project_routing_decision(decision)
        assert source == expected
    safe, _work_units, _source = queries.project_routing_decision(
        {"provider": "provider", "trace_id": "turn"}
    )
    assert safe["provider"] == "provider"
    safe, _work_units, _source = queries.project_routing_decision({"query_hash": "bad"})
    assert "query_hash" not in safe

    where, _parameters = queries.retention_predicates(
        "routing_decisions",
        queries.RUNTIME_TABLE_TIMESTAMPS["routing_decisions"],
        cutoff=None,
        keep_last=1,
    )
    assert "active" in where


def test_roster_versioned_prompt_rejection_paths(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agent = {
        "slug": "coverage-agent",
        "name": "Coverage Agent",
        "version": "1.0.0",
        "prompt_body": "Inspect exact branches.",
    }
    store._activate_prevalidated_agent(agent)
    active = next(
        item for item in store.get_active_roster() if item["agent_slug"] == "coverage-agent"
    )
    content_hash = str(active["hash"])

    assert store.get_versioned_specialist_prompt("coverage-agent", "1.0.0", "bad\x00") is None
    assert store.get_versioned_specialist_prompt("", "1.0.0", content_hash) is None
    assert store.get_versioned_specialist_prompt("coverage-agent", "", content_hash) is None
    assert store.get_versioned_specialist_prompt("missing", "1.0.0", content_hash) is None
    prompt = store.get_versioned_specialist_prompt(
        "coverage-agent",
        "1.0.0",
        content_hash,
        max_chars=4,
    )
    assert prompt is not None
    assert prompt["prompt_body"] == "Insp"
    assert prompt["prompt_truncated"] is True
