"""Exact branch coverage for the durable preflight Store lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.resident_manager_binding import (
    build_resident_control_epoch,
    build_resident_manager_binding,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL_REFERENCE,
    RESIDENT_MANAGER_SLUGS,
)
from agency_runtime.core.store import preflight as store_preflight
from agency_runtime.core.store.sqlite import Store

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_C = "c" * 64


def _routing(trace_id: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "query_hash": _DIGEST_A,
        "context_fingerprint": _DIGEST_B,
        "status": "abstained",
        "source": "coverage",
        "selected_ids": [],
        "semantic_ids": [],
        "available_companion_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "work_units": {
            "delegate": False,
            "count": 1,
            "confidence": "low",
            "source": "coverage",
        },
    }


def _ready_payload(
    trace_id: str,
    *,
    session_id: str = "session",
    refs: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    specialist_refs = [] if refs is None else refs
    routing = _routing(trace_id)
    projected = store_preflight._project_routing_evidence(routing, trace_id=trace_id)
    assert projected is not None
    recipe = {
        "recipe_version": 5,
        "policy_fingerprint": _DIGEST_C,
        "session_id": session_id,
        "trace_id": trace_id,
        "host": "codex",
        # `isolated` was deleted with its enforcement in d9f6e6be; `direct` is
        # the only mode `_project_preflight_recipe` accepts, and anything else
        # projects to None and reports as a mismatched replay recipe.
        "delivery_mode": "direct",
        "context_limit": 4_096,
        "routing": projected["decision"],
        "specialist_refs": specialist_refs,
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "trivial": False,
        "roster_size": len(specialist_refs),
    }
    return recipe, routing, specialist_refs


def test_preflight_projection_rejects_malformed_metadata_and_scalars() -> None:
    assert store_preflight._request_fingerprint(None) == ""
    assert store_preflight._request_fingerprint("{") == ""
    assert store_preflight._request_fingerprint("[]") == ""
    assert store_preflight._request_fingerprint('{"request_fingerprint":7}') == ""
    assert (
        store_preflight._request_fingerprint(json.dumps({"request_fingerprint": _DIGEST_A}))
        == _DIGEST_A
    )

    assert store_preflight._request_kind(None) == ""
    assert store_preflight._request_kind("{") == ""
    assert store_preflight._request_kind("[]") == ""
    assert store_preflight._request_kind('{"request_kind":"unknown"}') == ""
    assert store_preflight._request_kind('{"request_kind":"trivial"}') == "trivial"

    assert store_preflight._bounded_nonnegative_int(True, maximum=3) == 0
    assert store_preflight._bounded_nonnegative_int(object(), maximum=3) == 0
    assert store_preflight._bounded_finite_float(object()) == 0.0
    assert store_preflight._bounded_finite_float(float("inf")) == 0.0
    assert store_preflight._project_recipe_routing([], trace_id="turn") is None
    assert store_preflight._project_routing_evidence([], trace_id="turn") is None
    assert (
        store_preflight._project_routing_evidence(
            {"query_hash": "bad", "context_fingerprint": _DIGEST_B},
            trace_id="turn",
        )
        is None
    )


def test_specialist_ref_projections_reject_every_invalid_shape() -> None:
    max_refs = store_preflight.MAX_DURABLE_SPECIALIST_REFERENCES
    assert store_preflight._project_specialist_refs({}) is None
    assert store_preflight._project_specialist_refs([{}] * (max_refs + 1)) is None
    assert store_preflight._project_specialist_refs(["agent"]) is None
    assert (
        store_preflight._project_specialist_refs([{"slug": "", "version": "1", "hash": "h"}])
        is None
    )
    assert (
        store_preflight._project_specialist_refs(
            [
                {"slug": "agent", "version": "1", "hash": "h"},
                {"slug": "agent", "version": "2", "hash": "h2"},
            ]
        )
        is None
    )
    assert store_preflight._project_specialist_refs(
        [
            {
                "slug": "agent",
                "version": "1",
                "hash": "opaque",
                "capabilities": "not-a-list",
            }
        ]
    ) == [
        {
            "slug": "agent",
            "version": "1",
            "hash": "opaque",
            "description": "",
            "capabilities": [],
        }
    ]
    assert store_preflight._project_specialist_refs(
        [
            {
                "slug": "agent",
                "version": "1",
                "hash": "opaque",
                "capabilities": ["audit", "", "secure"],
            }
        ]
    )[0]["capabilities"] == ["audit", "secure"]
    immutable_version = "sha256:" + "a" * 64
    assert (
        store_preflight._project_specialist_refs(
            [{"slug": "agent", "version": immutable_version, "hash": "opaque"}]
        )[0]["version"]
        == immutable_version
    )
    assert (
        store_preflight._project_specialist_refs(
            [{"slug": "agent", "version": "v" * 257, "hash": "opaque"}]
        )
        is None
    )
    assert (
        store_preflight._project_specialist_refs(
            [{"slug": "a" * 129, "version": "1", "hash": "opaque"}]
        )
        is None
    )
    # A resident manager is never a durable specialist reference. The slug is
    # taken from RESIDENT_MANAGER_SLUGS rather than hardcoded: this assertion
    # used `agents-orchestrator`, which stopped being a resident manager when
    # that role was removed, so the branch it was written to cover was silently
    # no longer exercised.
    assert RESIDENT_MANAGER_SLUGS
    assert (
        store_preflight._project_specialist_refs(
            [{"slug": RESIDENT_MANAGER_SLUGS[0], "version": "1", "hash": "opaque"}]
        )
        is None
    )

    # The suggestion half of this test exercised `_project_suggestions`, which
    # 40c608dc deleted along with the rest of the unit_agent_plan plumbing.
    # There is no surviving behaviour to assert, so it is gone rather than
    # rewritten -- keeping it would only re-test a function that no longer
    # exists.
    assert not hasattr(store_preflight, "_project_suggestions")


def test_recipe_projection_and_decode_fail_closed() -> None:
    assert store_preflight._project_preflight_recipe([], session_id="s", trace_id="t") is None
    for bad_header in (
        {"recipe_version": True, "policy_fingerprint": _DIGEST_C, "trivial": False},
        {"recipe_version": 1, "policy_fingerprint": "bad", "trivial": False},
        {"recipe_version": 1, "policy_fingerprint": _DIGEST_C, "trivial": "no"},
    ):
        assert (
            store_preflight._project_preflight_recipe(
                bad_header,
                session_id="s",
                trace_id="t",
            )
            is None
        )
    invalid_children = {
        "recipe_version": 1,
        "policy_fingerprint": _DIGEST_C,
        "trivial": False,
        "specialist_refs": {},
        "routing": {},
    }
    assert (
        store_preflight._project_preflight_recipe(
            invalid_children,
            session_id="s",
            trace_id="t",
        )
        is None
    )
    recipe, _routing_evidence, _refs = _ready_payload("t", session_id="s")
    assert (
        store_preflight._project_preflight_recipe(
            {**recipe, "unit_assignment_agents": {}},
            session_id="s",
            trace_id="t",
        )
        is None
    )
    assert store_preflight._decode_preflight_recipe(None, session_id="s", trace_id="t") is None
    assert store_preflight._decode_preflight_recipe("{", session_id="s", trace_id="t") is None


def test_recipe_projection_requires_exact_v7_resident_kernel_and_rejects_legacy_leakage() -> None:
    recipe, _routing_evidence, _refs = _ready_payload("t", session_id="s")
    classification = {
        "turn_kind": "new_intent",
        "selection_required": True,
        "reroute_required": True,
        "execution_decision_required": True,
        "continuation_of": "",
        "confidence": 1.0,
        "reason_codes": ["test_fixture"],
        "state_revision": _DIGEST_A,
        "classifier_version": 1,
    }
    reference = RESIDENT_MANAGER_KERNEL_REFERENCE.as_dict()
    current = {
        **recipe,
        "recipe_version": 7,
        "turn_classification": classification,
        "resident_manager_kernel": reference,
    }
    assert (
        store_preflight._project_preflight_recipe(
            current,
            session_id="s",
            trace_id="t",
        )
        is not None
    )

    # The slug case was `list(reversed(...))`, which distinguishes nothing once
    # RESIDENT_MANAGER_SLUGS holds a single entry -- reversing one element
    # returns an identical, entirely valid reference. Substituting a foreign
    # slug keeps the branch meaningful at any roster size.
    for invalid in (
        None,
        {**reference, "version": 999},
        {**reference, "content_hash": _DIGEST_B},
        {**reference, "slugs": ["not-a-resident-manager"]},
        {**reference, "slugs": [*reference["slugs"], "not-a-resident-manager"]},
    ):
        assert (
            store_preflight._project_preflight_recipe(
                {**current, "resident_manager_kernel": invalid},
                session_id="s",
                trace_id="t",
            )
            is None
        )

    assert (
        store_preflight._project_preflight_recipe(
            {**recipe, "resident_manager_kernel": reference},
            session_id="s",
            trace_id="t",
        )
        is None
    )


@pytest.mark.parametrize("lease", [True, 0, store_preflight.MAX_HOOK_TIMEOUT_SECONDS + 1])
def test_preflight_clock_rejects_invalid_lease_budgets(tmp_path: Path, lease: Any) -> None:
    store = Store(tmp_path / "agency.db")
    conn = store._connect()
    try:
        with pytest.raises(ValueError, match="preflight lease budget"):
            store_preflight._preflight_clock(conn, lease)
    finally:
        conn.close()


def test_ready_evidence_validation_rejects_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe, routing, refs = _ready_payload("turn")
    common = {
        "session_id": "session",
        "trace_id": "turn",
        "attempt_token": "attempt",
        "host": "codex",
        "recipe": recipe,
        "routing_evidence": routing,
        "specialist_refs": refs,
    }
    with pytest.raises(ValueError, match="attempt_token"):
        store_preflight._prepare_ready_evidence(**{**common, "attempt_token": ""})
    with pytest.raises(ValueError, match="specialist replay"):
        store_preflight._prepare_ready_evidence(**{**common, "specialist_refs": [{"slug": ""}]})
    with pytest.raises(ValueError, match="recipe is invalid or mismatched"):
        store_preflight._prepare_ready_evidence(
            **{**common, "recipe": {**recipe, "specialist_refs": [{"slug": ""}]}}
        )
    with pytest.raises(ValueError, match="routing evidence"):
        store_preflight._prepare_ready_evidence(
            **{**common, "routing_evidence": {"query_hash": "bad"}}
        )
    mismatched_routing = {**routing, "status": "selected"}
    with pytest.raises(ValueError, match="do not match"):
        store_preflight._prepare_ready_evidence(
            **{**common, "routing_evidence": mismatched_routing}
        )
    ref = {"slug": "agent", "version": "1", "hash": "opaque"}
    ref_recipe, ref_routing, _ = _ready_payload("turn", refs=[ref])
    with pytest.raises(ValueError, match="roster size"):
        store_preflight._prepare_ready_evidence(
            **{
                **common,
                "recipe": {**ref_recipe, "roster_size": 0},
                "routing_evidence": ref_routing,
                "specialist_refs": [ref],
            }
        )
    # The `suggestions are invalid` and `work-unit metadata` rejections were
    # deleted with the unit_agent_plan plumbing in 40c608dc: `suggestions` is no
    # longer a parameter and `_project_suggestions` no longer exists, so neither
    # branch survives to be covered.

    monkeypatch.setattr(store_preflight, "_MAX_RECIPE_BYTES", 1)
    with pytest.raises(ValueError, match="bounded store limit"):
        store_preflight._prepare_ready_evidence(**common)


def _request(*, reservation_token: str = "") -> store_preflight._PreflightRequest:
    return store_preflight._PreflightRequest(
        session_id="session",
        trace_id="turn",
        reservation_token=reservation_token,
        fingerprint=_DIGEST_A,
        request_kind="nontrivial",
        host="codex",
        user_message="",
        metadata="{}",
    )


class _ZeroRowConnection:
    def execute(self, *_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(rowcount=0)


def test_preflight_helper_conflicts_and_atomicity_guards(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    stale = store._insert_preflight_attempt(
        _ZeroRowConnection(),
        _request(reservation_token="token"),
        now_value="now",
        lease_expires_at="later",
    )
    assert stale["outcome"] == "stale_reservation"
    promoted = store._promote_preflight_reservation(
        _ZeroRowConnection(),
        {"id": "run"},
        _request(),
        state="",
        stored_reservation="",
        now_value="now",
        lease_expires_at="later",
    )
    assert promoted["outcome"] == "stale_reservation"
    with pytest.raises(RuntimeError, match="promotion lost atomicity"):
        store._promote_preflight_reservation(
            _ZeroRowConnection(),
            {"id": "run"},
            _request(reservation_token="token"),
            state="reserved",
            stored_reservation="token",
            now_value="now",
            lease_expires_at="later",
        )
    with pytest.raises(RuntimeError, match="recovery lost atomicity"):
        store._recover_expired_preflight(
            _ZeroRowConnection(),
            {"id": "run"},
            _request(),
            prior_attempt_token="old",
            now_value="now",
            lease_expires_at="later",
        )


def test_begin_preflight_reports_uninitialized_conflicts_and_terminal_states(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        store.begin_preflight_attempt(
            session_id="session",
            trace_id="bad-fingerprint",
            request_fingerprint="bad",
            request_kind="nontrivial",
        )
    with pytest.raises(ValueError, match="request_kind"):
        store.begin_preflight_attempt(
            session_id="session",
            trace_id="bad-kind",
            request_fingerprint=_DIGEST_A,
            request_kind="other",
        )

    store.create_run(trace_id="uninitialized", session_id="session")
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="uninitialized",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    assert started["outcome"] == "started"

    store.create_run(trace_id="conflict", session_id="session")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE runs SET metadata = ? WHERE trace_id = 'conflict'",
            (json.dumps({"request_fingerprint": _DIGEST_B, "request_kind": "trivial"}),),
        )
        conn.commit()
    finally:
        conn.close()
    conflict = store.begin_preflight_attempt(
        session_id="session",
        trace_id="conflict",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    assert conflict["outcome"] == "conflict"

    store.create_run(trace_id="invalid-state", session_id="session")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE runs SET preflight_state = 'invalid', "
            "preflight_request_fingerprint = ?, preflight_request_kind = ? "
            "WHERE trace_id = 'invalid-state'",
            (_DIGEST_A, "nontrivial"),
        )
        conn.commit()
    finally:
        conn.close()
    invalid = store.begin_preflight_attempt(
        session_id="session",
        trace_id="invalid-state",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    assert invalid["outcome"] == "conflict"

    terminal_id = store.create_run(trace_id="terminal", session_id="session")
    store.complete_run(terminal_id)
    terminal = store.begin_preflight_attempt(
        session_id="session",
        trace_id="terminal",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    assert terminal["outcome"] == "terminal"

    other_session = store._begin_existing_preflight(
        _ZeroRowConnection(),
        {
            "session_id": "other",
            "status": "active",
            "preflight_state": "",
            "reservation_token": "",
        },
        _request(),
        now_value="now",
        lease_expires_at="later",
    )
    assert other_session["outcome"] == "conflict"


def test_begin_preflight_defends_against_empty_normalized_correlation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    monkeypatch.setattr(store_preflight, "validate_correlation_id", lambda *_args, **_kwargs: "")
    with pytest.raises(ValueError, match="required for preflight"):
        store.begin_preflight_attempt(
            session_id="session",
            trace_id="turn",
            request_fingerprint=_DIGEST_A,
            request_kind="nontrivial",
        )


def test_observe_fail_abandon_and_ready_replay_edges(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    assert store.observe_preflight_attempt("", "turn", "attempt") is None
    assert store.observe_preflight_attempt("session", "missing", "attempt") is None
    assert store.get_ready_preflight_result("session", "missing", "attempt") is None
    with pytest.raises(ValueError, match="terminal status"):
        store.fail_preflight_attempt(
            session_id="session",
            trace_id="turn",
            attempt_token="attempt",
            status="active",
        )
    with pytest.raises(ValueError, match="preflight terminal status"):
        store.abandon_preflight_reservation(
            session_id="session",
            trace_id="turn",
            reservation_token="token",
            status="completed",
        )

    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="ready",
        host="codex",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    recipe, routing, refs = _ready_payload("ready")
    kwargs = {
        "session_id": "session",
        "trace_id": "ready",
        "attempt_token": started["attempt_token"],
        "recipe": recipe,
        "host": "codex",
        "routing_evidence": routing,
        "specialist_refs": refs,
    }
    assert store.mark_preflight_ready(**kwargs) == {"outcome": "committed"}
    assert store.mark_preflight_ready(**kwargs) == {"outcome": "replay"}
    conn = store._connect()
    try:
        conn.execute("UPDATE runs SET preflight_result = '{' WHERE trace_id = 'ready'")
        conn.commit()
    finally:
        conn.close()
    assert store.mark_preflight_ready(**kwargs) == {"outcome": "cas_lost"}
    conflict = store.begin_preflight_attempt(
        session_id="session",
        trace_id="ready",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    assert conflict["outcome"] == "conflict"


def test_mark_preflight_ready_atomically_commits_projected_provider_receipts(
    tmp_path: Path,
) -> None:
    from agency_runtime.core.preflight_recipe import _content_free_routing_recipe

    store = Store(tmp_path / "agency.db")
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="provider-receipts",
        host="codex",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    recipe, routing, refs = _ready_payload("provider-receipts")
    routing["provider_attempts"] = [
        {
            "provider_name": "codex-subscription",
            "provider_type": "cli",
            "requested_model": "gpt-5.6-luna",
            "model_group": "planning",
            "actual_model": "gpt-5.6-luna",
            "model_receipt_source": "cli.explicit_model_argument",
            "status": "applied",
            "reason_code": "",
        },
        {
            "provider_name": "fallback-provider",
            "provider_type": "http",
            "requested_model": "fallback-model",
            "model_group": "planning",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "failed",
            "reason_code": "provider_unavailable",
        },
    ]
    routing_recipe = _content_free_routing_recipe(routing, trace_id="provider-receipts")
    assert routing_recipe["model_receipt_attempts"] == routing["provider_attempts"]

    kwargs = {
        "session_id": "session",
        "trace_id": "provider-receipts",
        "attempt_token": started["attempt_token"],
        "recipe": {**recipe, "routing": routing_recipe},
        "host": "codex",
        "routing_evidence": routing_recipe,
        "specialist_refs": refs,
    }
    assert store.mark_preflight_ready(**kwargs) == {"outcome": "committed"}
    assert store.mark_preflight_ready(**kwargs) == {"outcome": "replay"}

    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT requested_model, model_group, resolved_provider, resolved_model, "
            "attempted_fallbacks, source, status FROM model_receipts "
            "WHERE trace_id = ? ORDER BY attempted_fallbacks",
            ("provider-receipts",),
        ).fetchall()
    finally:
        conn.close()
    assert [dict(row) for row in rows] == [
        {
            "requested_model": "gpt-5.6-luna",
            "model_group": "planning",
            "resolved_provider": "codex-subscription",
            "resolved_model": "gpt-5.6-luna",
            "attempted_fallbacks": 0,
            "source": "wrapper",
            "status": "success",
        },
        {
            "requested_model": "fallback-model",
            "model_group": "planning",
            "resolved_provider": "fallback-provider",
            "resolved_model": "unavailable",
            "attempted_fallbacks": 1,
            "source": "wrapper",
            "status": "failed",
        },
    ]


class _QueryResult:
    def __init__(self, row: Any = None, *, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row


class _ReadyCasConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _QueryResult:
        if "SELECT STRFTIME" in sql:
            return _QueryResult({"now_value": "2026-01-01T00:00:00+00:00"})
        if "SELECT status, host, preflight_state" in sql:
            return _QueryResult(
                {
                    "status": "active",
                    "host": "codex",
                    "preflight_state": "in_progress",
                    "preflight_attempt_token": "attempt",
                    "preflight_lease_expires_at": "2099-01-01T00:00:00+00:00",
                    "preflight_result": "",
                }
            )
        if "UPDATE runs SET preflight_state = 'ready'" in sql:
            return _QueryResult(rowcount=0)
        return _QueryResult()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_mark_preflight_ready_handles_compare_and_swap_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _ReadyCasConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    recipe, routing, refs = _ready_payload("turn")
    assert store.mark_preflight_ready(
        session_id="session",
        trace_id="turn",
        attempt_token="attempt",
        recipe=recipe,
        host="codex",
        routing_evidence=routing,
        specialist_refs=refs,
    ) == {"outcome": "cas_lost"}
    assert connection.rolled_back is True
    assert connection.closed is True


def test_mark_preflight_ready_rejects_a_different_stored_host(tmp_path: Path) -> None:
    store = Store(tmp_path / "host-conflict.db")
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="turn",
        host="claude",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    recipe, routing, refs = _ready_payload("turn")

    assert store.mark_preflight_ready(
        session_id="session",
        trace_id="turn",
        attempt_token=started["attempt_token"],
        recipe=recipe,
        host="codex",
        routing_evidence=routing,
        specialist_refs=refs,
    ) == {"outcome": "host_conflict"}


class _FailingConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("synthetic database failure")

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("operation", ["begin", "fail", "abandon", "ready"])
def test_preflight_mutations_rollback_and_close_on_database_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _FailingConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    recipe, routing, refs = _ready_payload("turn")
    with pytest.raises(RuntimeError, match="synthetic database failure"):
        if operation == "begin":
            store.begin_preflight_attempt(
                session_id="session",
                trace_id="turn",
                request_fingerprint=_DIGEST_A,
                request_kind="nontrivial",
            )
        elif operation == "fail":
            store.fail_preflight_attempt(
                session_id="session",
                trace_id="turn",
                attempt_token="attempt",
            )
        elif operation == "abandon":
            store.abandon_preflight_reservation(
                session_id="session",
                trace_id="turn",
                reservation_token="reservation",
            )
        else:
            store.mark_preflight_ready(
                session_id="session",
                trace_id="turn",
                attempt_token="attempt",
                recipe=recipe,
                host="codex",
                routing_evidence=routing,
                specialist_refs=refs,
            )
    assert connection.rolled_back is True
    assert connection.closed is True


def _turn_classification(
    *,
    turn_kind: str = "new_intent",
    continuation_of: str = "",
    reasons: object = None,
) -> dict[str, Any]:
    decisions = (
        {
            "selection_required": True,
            "reroute_required": False,
            "execution_decision_required": True,
        }
        if turn_kind == "continuation"
        else {
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
        }
    )
    return {
        "turn_kind": turn_kind,
        **decisions,
        "continuation_of": continuation_of,
        "confidence": 1.0,
        "reason_codes": ["coverage"] if reasons is None else reasons,
        "state_revision": _DIGEST_A,
        "classifier_version": 1,
    }


def _resident_recipe(
    trace_id: str,
    *,
    version: int = 9,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    recipe, routing, refs = _ready_payload(trace_id)
    binding = build_resident_manager_binding(
        session_id="session",
        host="codex",
        delivery_mode="request",
        control_epoch=build_resident_control_epoch(),
    )
    recipe.update(
        recipe_version=version,
        turn_classification=_turn_classification(),
        resident_manager_binding=binding.as_dict(),
    )
    if version >= 10:
        recipe.update(selection_refs=[], roster_generation=0)
    return recipe, routing, refs


def test_turn_classification_rejects_every_invalid_shape_and_deduplicates_reasons() -> None:
    assert (
        store_preflight._project_turn_classification(
            {**_turn_classification(), "classifier_version": True}
        )
        is None
    )
    assert (
        store_preflight._project_turn_classification(
            _turn_classification(
                turn_kind="continuation",
                continuation_of="bad\x00trace",
            )
        )
        is None
    )
    assert (
        store_preflight._project_turn_classification(
            {
                **_turn_classification(turn_kind="control"),
                "selection_required": True,
            }
        )
        is None
    )
    assert (
        store_preflight._project_turn_classification(
            _turn_classification(reasons={"not": "a list"})
        )
        is None
    )
    assert (
        store_preflight._project_turn_classification(_turn_classification(reasons=["INVALID"]))
        is None
    )
    projected = store_preflight._project_turn_classification(
        _turn_classification(reasons=["coverage", "coverage"])
    )
    assert projected is not None
    assert projected["reason_codes"] == ["coverage"]


def test_turn_classification_versions_pure_social_bypass_without_rewriting_v3() -> None:
    social = {
        **_turn_classification(turn_kind="conversation"),
        "selection_required": False,
        "reroute_required": False,
        "execution_decision_required": False,
        "message_fingerprint": _DIGEST_B,
    }

    assert store_preflight._project_turn_classification({**social, "classifier_version": 3}) is None
    projected = store_preflight._project_turn_classification({**social, "classifier_version": 4})
    assert projected is not None
    assert projected["turn_kind"] == "conversation"
    assert projected["selection_required"] is False


def test_continuation_guard_and_resident_kernel_reject_invalid_projections() -> None:
    valid_guard = {
        "guard_version": 1,
        "source_trace_id": "source",
        "source_turn_sequence": 1,
        "source_evidence_revision": 1,
        "source_roster_generation": 0,
        "source_recipe_digest": _DIGEST_A,
        "source_routing_digest": _DIGEST_A,
        "routing_fingerprint": _DIGEST_A,
        "context_policy_fingerprint": _DIGEST_A,
        "selection_digest": _DIGEST_A,
        "delegation_digest": _DIGEST_A,
    }
    assert store_preflight._project_continuation_guard({}) is None
    assert (
        store_preflight._project_continuation_guard(
            {**valid_guard, "source_trace_id": "bad\x00trace"}
        )
        is None
    )
    assert (
        store_preflight._project_continuation_guard({**valid_guard, "source_turn_sequence": True})
        is None
    )
    assert (
        store_preflight._project_continuation_guard({**valid_guard, "delegation_digest": "bad"})
        is None
    )
    assert (
        store_preflight._project_resident_manager_kernel(
            {"version": True, "content_hash": _DIGEST_A, "slugs": ["a", "b"]}
        )
        is None
    )
    assert (
        store_preflight._project_resident_manager_kernel(
            {"version": 1, "content_hash": _DIGEST_A, "slugs": ["a", "a"]}
        )
        is None
    )


def test_recipe_projection_rejects_invalid_binding_and_unguarded_reuse() -> None:
    recipe, _routing_evidence, _refs = _resident_recipe("turn")
    assert (
        store_preflight._project_preflight_recipe(
            {**recipe, "resident_manager_binding": {"invalid": True}},
            session_id="session",
            trace_id="turn",
        )
        is None
    )

    continuation, _routing_evidence, _refs = _resident_recipe("turn", version=10)
    continuation["routing"] = {
        **continuation["routing"],
        "continuation_reused": True,
    }
    assert (
        store_preflight._project_preflight_recipe(
            continuation,
            session_id="session",
            trace_id="turn",
        )
        is None
    )


def test_ready_evidence_rejects_host_mismatch() -> None:
    recipe, routing, refs = _ready_payload("turn")
    with pytest.raises(ValueError, match="ready host"):
        store_preflight._prepare_ready_evidence(
            session_id="session",
            trace_id="turn",
            attempt_token="attempt",
            host="claude",
            recipe=recipe,
            routing_evidence=routing,
            specialist_refs=refs,
        )
    # The `unit-agent plan` rejection went with the unit_agent_plan plumbing in
    # 40c608dc. The matching host case above is the surviving branch; a second
    # call with a valid host now simply succeeds, so asserting it raises tested
    # nothing that still exists.


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class _RowsConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def execute(self, *_args: Any, **_kwargs: Any) -> _RowsResult:
        return _RowsResult(self.rows)


@pytest.mark.parametrize("decision", [None, "{", "[]"])
def test_routing_component_rejects_missing_malformed_or_nonobject_decisions(
    decision: str | None,
) -> None:
    rows = (
        []
        if decision is None
        else [
            {
                "query_hash": _DIGEST_A,
                "context_fingerprint": _DIGEST_B,
                "source": "coverage",
                "decision": decision,
            }
        ]
    )
    assert (
        store_preflight._routing_component_matches(
            _RowsConnection(rows),
            session_id="session",
            trace_id="turn",
            routing={},
        )
        is False
    )


class _ContinuationConnection:
    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _QueryResult:
        if "SELECT turn_sequence FROM runs" in sql:
            return _QueryResult({"turn_sequence": 2})
        if "SELECT session_id, host, status" in sql:
            return _QueryResult(
                {
                    "session_id": "session",
                    "host": "codex",
                    "status": "active",
                    "preflight_state": "ready",
                    "preflight_result": "{}",
                    "evidence_revision": 1,
                    "turn_sequence": 1,
                }
            )
        return _QueryResult({"value": 0})


def _continuation_recipe() -> dict[str, Any]:
    return {
        "recipe_version": store_preflight.PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": _DIGEST_B,
        "roster_generation": 0,
        "routing": {
            "context_fingerprint": _DIGEST_A,
            "continuation_resolution_required": False,
        },
        "selection_refs": [],
        "unit_agent_plan": [],
    }


def test_continuation_snapshot_rejects_routing_and_plan_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _ContinuationConnection()
    monkeypatch.setattr(
        store_preflight,
        "_decode_preflight_recipe",
        lambda *_args, **_kwargs: _continuation_recipe(),
    )
    monkeypatch.setattr(
        store_preflight,
        "_routing_component_matches",
        lambda *_args, **_kwargs: False,
    )
    assert (
        store_preflight._continuation_source_snapshot(
            connection,
            session_id="session",
            trace_id="turn",
            source_trace_id="source",
            host="codex",
            routing_fingerprint=_DIGEST_A,
            context_policy_fingerprint=_DIGEST_B,
            roster_generation=0,
        )
        is None
    )

    monkeypatch.setattr(
        store_preflight,
        "_routing_component_matches",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        store_preflight,
        "_delegation_component",
        lambda *_args, **_kwargs: (
            [{"work_unit_id": "unit", "recommended_agent": "agent"}],
            _DIGEST_C,
            True,
        ),
    )
    assert (
        store_preflight._continuation_source_snapshot(
            connection,
            session_id="session",
            trace_id="turn",
            source_trace_id="source",
            host="codex",
            routing_fingerprint=_DIGEST_A,
            context_policy_fingerprint=_DIGEST_B,
            roster_generation=0,
        )
        is None
    )


def test_continuation_guard_and_public_resolution_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert store_preflight._continuation_guard_matches(_RowsConnection([]), {}) is False
    store = Store(tmp_path / "agency.db")
    assert (
        store.resolve_durable_continuation(
            session_id="session",
            trace_id="turn",
            source_trace_id="source",
            host="codex",
            routing_fingerprint="bad",
            context_policy_fingerprint=_DIGEST_A,
            roster_generation=0,
        )
        is None
    )

    connection = _FailingConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    with pytest.raises(RuntimeError, match="synthetic database"):
        store.resolve_durable_continuation(
            session_id="session",
            trace_id="turn",
            source_trace_id="source",
            host="codex",
            routing_fingerprint=_DIGEST_A,
            context_policy_fingerprint=_DIGEST_B,
            roster_generation=0,
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_begin_and_ready_receipt_reject_invalid_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="turn_classification"):
        store.begin_preflight_attempt(
            session_id="session",
            trace_id="invalid-turn",
            request_fingerprint=_DIGEST_A,
            request_kind="nontrivial",
            turn_classification={},
        )
    with pytest.raises(ValueError, match="evidence_revision"):
        store.get_ready_routing_receipt(
            "session",
            "turn",
            evidence_revision=True,
        )
    assert (
        store.get_ready_routing_receipt(
            "session",
            "missing",
            evidence_revision=1,
        )
        is None
    )

    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="corrupt-ready",
        host="codex",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    recipe, routing, refs = _ready_payload("corrupt-ready")
    assert store.mark_preflight_ready(
        session_id="session",
        trace_id="corrupt-ready",
        attempt_token=started["attempt_token"],
        recipe=recipe,
        host="codex",
        routing_evidence=routing,
        specialist_refs=refs,
    ) == {"outcome": "committed"}
    conn = store._connect()
    try:
        conn.execute("UPDATE runs SET preflight_result = '{' WHERE trace_id = 'corrupt-ready'")
        conn.commit()
        revision = int(
            conn.execute(
                "SELECT evidence_revision FROM runs WHERE trace_id = 'corrupt-ready'"
            ).fetchone()["evidence_revision"]
        )
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="recipe failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            "corrupt-ready",
            evidence_revision=revision,
        )


def test_mark_ready_rolls_back_a_resident_binding_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="binding-conflict",
        host="codex",
        request_fingerprint=_DIGEST_A,
        request_kind="nontrivial",
    )
    recipe, routing, refs = _resident_recipe("binding-conflict")
    monkeypatch.setattr(
        store,
        "_commit_resident_manager_binding",
        lambda *_args, **_kwargs: False,
    )
    assert store.mark_preflight_ready(
        session_id="session",
        trace_id="binding-conflict",
        attempt_token=started["attempt_token"],
        recipe=recipe,
        host="codex",
        routing_evidence=routing,
        specialist_refs=refs,
    ) == {"outcome": "binding_conflict"}
