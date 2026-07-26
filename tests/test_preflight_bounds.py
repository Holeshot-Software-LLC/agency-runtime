"""Adversarial correlation and resource-bound regressions for preflight."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime import AgencyRuntime
from agency_runtime.core import preflight_recipe
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.delegation.events import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_WORK_UNIT_CHARS,
    record_suggested_delegations,
)
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.resident_manager_binding import build_resident_manager_binding
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_SLUGS,
)
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.delegation_detection import (
    MAX_WORK_UNIT_INPUT_CHARS,
    detect_work_units,
)
from agency_runtime.core.specialist_context import _prompt_context_lines
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import native_adapter_turn_origin


def test_direct_specialist_capsule_preserves_exact_prompt_whitespace() -> None:
    prompt_body = "  exact leading whitespace\ntrailing whitespace  \n"
    rendered = "\n".join(
        _prompt_context_lines(
            {
                "slug": "code-reviewer",
                "description": "Reviews code.",
                "prompt_body": prompt_body,
            }
        )
    )

    assert prompt_body in rendered


def test_preflight_persists_request_kind_and_terminalizes_downstream_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def fail_route(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("routing unavailable")

    monkeypatch.setattr(pipeline, "route", fail_route)

    with pytest.raises(RuntimeError, match="routing unavailable"):
        run_preflight(
            store,
            session_id="session",
            user_message="Audit and harden the runtime.",
            host="codex",
            trace_id="failed-turn",
        )

    assert store.get_turn_request_kind("session", "failed-turn") == "nontrivial"
    assert store.get_run("failed-turn")["status"] == "preflight_failed"
    assert store.get_open_traces_for_session("session") == []


@pytest.mark.parametrize("failure", ["config", "classification", "begin_attempt"])
def test_early_preflight_failure_closes_its_hook_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    reservation = store.reserve_session_turn(
        session_id="session",
        trace_id="reserved",
        host="codex",
    )
    if failure == "config":
        monkeypatch.setattr(
            "agency_runtime.core.config_binding.load_config",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("config unavailable")),
        )
    elif failure == "classification":
        monkeypatch.setattr(
            "agency_runtime.core.preflight.classify_turn_intent",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("classification unavailable")
            ),
        )
    else:
        monkeypatch.setattr(
            store,
            "begin_preflight_attempt",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("create unavailable")),
        )

    with pytest.raises(RuntimeError, match="unavailable"):
        run_preflight(
            store,
            session_id="session",
            user_message="Audit and harden the runtime.",
            host="codex",
            trace_id="reserved",
            reservation_token=reservation["reservation_token"],
        )

    assert store.get_run("reserved")["status"] == "preflight_failed"
    assert store.get_open_traces_for_session("session") == []


def test_stale_reservation_token_cannot_promote_or_abandon_current_reservation(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    reservation = store.reserve_session_turn(
        session_id="session",
        trace_id="reserved",
        host="codex",
    )
    stale_token = "00000000-0000-4000-8000-000000000000"

    with pytest.raises(RuntimeError, match="stale_reservation"):
        run_preflight(
            store,
            session_id="session",
            user_message="Audit the runtime.",
            host="codex",
            trace_id="reserved",
            reservation_token=stale_token,
        )

    assert (
        store.abandon_preflight_reservation(
            session_id="session",
            trace_id="reserved",
            reservation_token=stale_token,
        )
        is False
    )
    connection = store._connect()
    try:
        lifecycle = connection.execute(
            "SELECT status, preflight_state, reservation_token FROM runs "
            "WHERE trace_id = 'reserved'"
        ).fetchone()
    finally:
        connection.close()
    assert lifecycle["status"] == "evidence_only"
    assert lifecycle["preflight_state"] == "reserved"
    assert lifecycle["reservation_token"] == reservation["reservation_token"]


def test_preflight_fingerprint_conflict_preserves_existing_active_turn(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    original_message = "Original request"
    first = run_preflight(
        store,
        session_id="session",
        user_message=original_message,
        host="codex",
        trace_id="active",
    )
    assert first.trace_id == "active"
    original = store.get_run("active")

    with pytest.raises(ValueError, match="different preflight request"):
        run_preflight(
            store,
            session_id="session",
            user_message="Different request",
            host="codex",
            trace_id="active",
        )

    assert store.get_run("active") == original
    assert store.get_open_traces_for_session("session") == ["active"]


def test_preflight_persists_trivial_kind_and_bounds_isolated_parent_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    routing = {
        "trace_id": "bounded-turn",
        "selected_ids": [],
        "query_hash": hashlib.sha256(b"thanks").hexdigest(),
        "context_fingerprint": "c" * 64,
        "work_units": detect_work_units("thanks"),
    }
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: routing)
    monkeypatch.setattr(
        pipeline,
        "build_routing_context",
        lambda *_args, **_kwargs: pytest.fail(
            "isolated preflight must not build direct routing context"
        ),
    )

    from agency_runtime.core import specialist_context

    monkeypatch.setattr(
        specialist_context,
        "hydrate_selected_specialist_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            context="s" * 100_000,
            slugs=(),
            references=(),
        ),
    )

    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="adapter_preflight",
        session_id="session",
        trace_id="bounded-turn",
    )
    result = run_preflight(
        store,
        session_id="session",
        user_message="thanks",
        host="codex",
        trace_id="bounded-turn",
        origin_receipt=origin_receipt,
    )

    assert result.trivial is True
    assert store.get_turn_request_kind("session", "bounded-turn") == "trivial"
    assert result.context.startswith(RESIDENT_MANAGER_KERNEL)
    assert "[AGENCY PREFLIGHT] Current isolated turn" in result.context
    assert len(result.context) <= 4_096
    assert "r" * 100 not in result.context
    assert "s" * 100 not in result.context
    assert "Agency/Agencies loaded:" in result.context
    assert "Agency/Agencies delegated:" in result.context
    assert "Actual Model selected:" in result.context
    assert result.context.index("Agency/Agencies loaded:") < result.context.index(
        "Agency/Agencies delegated:"
    )
    assert result.loaded_specialists == ()


def test_oversized_complete_context_fails_before_ready_is_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import specialist_context

    store = Store(tmp_path / "oversized-context.db")
    monkeypatch.setattr(
        specialist_context,
        "format_isolated_specialist_context",
        lambda *_args, **_kwargs: "x" * 20_000,
    )

    with pytest.raises(RuntimeError, match="exceeds the host delivery ceiling"):
        run_preflight(
            store,
            session_id="session",
            user_message="Review the runtime",
            host="codex",
            trace_id="oversized-context",
        )

    run = store.get_run("oversized-context")
    assert run is not None
    assert run["status"] == "preflight_failed"
    connection = store._connect()
    try:
        state = connection.execute(
            "SELECT preflight_state FROM runs WHERE trace_id = ?",
            ("oversized-context",),
        ).fetchone()["preflight_state"]
    finally:
        connection.close()
    assert state != "ready"


def test_direct_preflight_never_concatenates_unrelated_specialist_instructions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "direct.db")
    for slug, prompt in (
        ("implementer", "IMPLEMENTER-ONLY-DIRECTIVE"),
        ("independent-reviewer", "REVIEWER-ONLY-DIRECTIVE"),
    ):
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "description": slug,
                "prompt_body": prompt,
                "version": "1.0.0",
            }
        )
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": ["implementer", "independent-reviewer"],
            "confidence": 0.9,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(
                b"Implement and independently review the change"
            ).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units("Implement and independently review the change"),
        },
    )

    result = run_preflight(
        store,
        session_id="direct-session",
        user_message="Implement and independently review the change",
        host="litellm",
        trace_id="direct-turn",
    )

    assert result.loaded_specialists == ("implementer",)
    assert "IMPLEMENTER-ONLY-DIRECTIVE" in result.context
    assert "REVIEWER-ONLY-DIRECTIVE" not in result.context


def test_direct_preflight_filters_resident_managers_before_selecting_a_specialist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "manager-first.db")
    store._activate_prevalidated_agent(
        {
            "slug": "implementer",
            "name": "Implementer",
            "description": "Implements bounded changes.",
            "prompt_body": "REAL-SPECIALIST-DIRECTIVE",
            "version": "1.0.0",
        }
    )
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": ["agents-orchestrator", "implementer", "chief-of-staff"],
            "confidence": 0.9,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(b"Implement the change").hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units("Implement the change"),
        },
    )

    result = run_preflight(
        store,
        session_id="manager-first-session",
        user_message="Implement the change",
        host="litellm",
        trace_id="manager-first-turn",
    )

    assert result.loaded_specialists == ("implementer",)
    assert result.selected_specialists == ("implementer",)
    assert result.resident_managers == RESIDENT_MANAGER_SLUGS
    assert "REAL-SPECIALIST-DIRECTIVE" in result.context


def test_direct_preflight_uses_resident_kernel_for_governed_fallback_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "fallback.db")
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": ["agents-orchestrator", "chief-of-staff"],
            "confidence": 0.0,
            "status": "policy_fallback",
            "source": "policy_fallback",
            "query_hash": hashlib.sha256(b"Handle an unfamiliar request").hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units("Handle an unfamiliar request"),
        },
    )

    result = run_preflight(
        store,
        session_id="fallback-session",
        user_message="Handle an unfamiliar request",
        host="hermes",
        trace_id="fallback-turn",
    )

    assert result.loaded_specialists == ()
    assert result.selected_specialists == ()
    assert result.resident_managers == RESIDENT_MANAGER_SLUGS
    assert RESIDENT_MANAGER_KERNEL in result.context
    assert store.get_specialists_for_session("fallback-session") == []


def test_ready_recipe_and_atomic_routing_evidence_never_persist_request_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    secret = "ULTRA-SECRET-UNIT-TEXT"
    message = f"1. audit authentication {secret}\n2. harden dashboard transport {secret}"
    work_units = detect_work_units(message)
    malicious_routing = {
        "trace_id": "private-ready",
        "selected_ids": [],
        "confidence": 0.0,
        "status": "abstained",
        "source": "test",
        "provider": f"provider-{secret}",
        "error": f"error-{secret}",
        "query_hash": hashlib.sha256(message.encode()).hexdigest(),
        "context_fingerprint": "c" * 64,
        "work_units": work_units,
    }
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: malicious_routing,
    )

    result = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="private-ready",
    )
    assert result.trace_id == "private-ready"

    connection = store._connect()
    try:
        run = connection.execute(
            "SELECT preflight_result FROM runs WHERE trace_id = 'private-ready'"
        ).fetchone()
        routing = connection.execute(
            "SELECT decision, work_units FROM routing_decisions WHERE trace_id = 'private-ready'"
        ).fetchone()
    finally:
        connection.close()

    raw_recipe = str(run["preflight_result"])
    assert secret not in raw_recipe
    recipe = json.loads(raw_recipe)
    assert "provider" not in recipe["routing"]
    assert "error" not in recipe["routing"]
    assert "units" not in recipe["routing"]["work_units"]
    assert secret not in str(routing["decision"])
    assert secret not in str(routing["work_units"])


def test_duplicate_ready_preflight_replays_without_selector_or_evidence_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    message = "Review the runtime lifecycle."
    route_calls = 0

    def route_once(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal route_calls
        route_calls += 1
        return {
            "trace_id": "ready-replay",
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(pipeline, "route", route_once)
    first = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="ready-replay",
    )
    counts_after_first = store.runtime_table_counts()
    second = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="ready-replay",
    )

    assert second.as_dict() == first.as_dict()
    assert route_calls == 1
    assert store.runtime_table_counts() == counts_after_first
    run = store.get_run("ready-replay")
    assert run["status"] == "active"
    connection = store._connect()
    try:
        lifecycle = connection.execute(
            "SELECT preflight_state, preflight_attempt_token FROM runs "
            "WHERE trace_id = 'ready-replay'"
        ).fetchone()
    finally:
        connection.close()
    assert lifecycle["preflight_state"] == "ready"
    assert lifecycle["preflight_attempt_token"]


@pytest.mark.skipif(
    sys.platform == "linux",
    reason="ADR-0087: the _coherent_workforce_snapshot stub returns an empty "
    "workforce; on Linux this triggers abstention before the CAS-loss assertion. "
    "Passes on Windows. Needs a Linux-specific stub or workforce seeding.",
)
def test_ready_replay_uses_immutable_prompt_and_persisted_roster_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.runtime_support import stub_inference_invoker, write_provider_config

    # ADR-0087: selection runs inference only when a provider is configured.
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    from agency_runtime.core.config import load_config, reset_config_cache

    reset_config_cache()
    store = Store(tmp_path / "agency.db")
    message = "Review this security patch."
    deterministic_config = load_config(config_path)
    capability_receipt = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id="session",
        trace_id="versioned-ready",
    )
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        first = run_preflight(
            store,
            session_id="session",
            user_message=message,
            host="codex",
            trace_id="versioned-ready",
            config=deterministic_config,
            capability_receipt=capability_receipt,
        )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
    assert "code-reviewer" in first.selected_specialists, first.routing
    assert first.loaded_specialists == ()
    connection = store._connect()
    try:
        persisted = connection.execute(
            "SELECT preflight_result FROM runs WHERE trace_id = 'versioned-ready'"
        ).fetchone()["preflight_result"]
        prompt_body = connection.execute(
            "SELECT content FROM agent_versions WHERE agent_slug = 'code-reviewer' "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()["content"]
    finally:
        connection.close()
    assert str(prompt_body) not in str(persisted)
    assert str(prompt_body) not in first.context
    assert store.get_specialists_for_trace("session", "versioned-ready") == []
    store.deactivate_agent("code-reviewer")

    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ready replay must not rerun routing")
        ),
    )
    second = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="versioned-ready",
        config=deterministic_config,
        capability_receipt=capability_receipt,
    )

    assert second.as_dict() == first.as_dict()
    assert "code-reviewer" in second.context
    assert str(prompt_body) not in second.context


def test_ready_replay_fails_closed_under_changed_context_policy(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    store = Store(tmp_path / "agency.db")
    message = "Review this security patch."
    original_config = AgencyConfig()
    run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="policy-bound",
        config=original_config,
    )
    changed_config = replace(
        original_config,
        selector=replace(
            original_config.selector,
            min_confidence=original_config.selector.min_confidence + 0.01,
        ),
    )

    with pytest.raises(RuntimeError, match="policy fingerprint"):
        run_preflight(
            store,
            session_id="session",
            user_message=message,
            host="codex",
            trace_id="policy-bound",
            config=changed_config,
        )

    connection = store._connect()
    try:
        state = connection.execute(
            "SELECT status, preflight_state FROM runs WHERE trace_id = 'policy-bound'"
        ).fetchone()
    finally:
        connection.close()
    assert state["status"] == "active"
    assert state["preflight_state"] == "ready"


@pytest.mark.parametrize("owner_fails", [False, True])
def test_concurrent_duplicate_preflights_share_one_owner_and_one_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    owner_fails: bool,
) -> None:
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    seed_starter_roster(store)
    message = "Audit the runtime lifecycle."
    reservation = store.reserve_session_turn(
        session_id="session",
        trace_id="shared-attempt",
        host="codex",
    )
    owner_started = Event()
    observer_started = Event()
    release_route = Event()
    route_lock = Lock()
    route_calls = 0
    original_begin = store.begin_preflight_attempt

    def observed_begin(**kwargs: Any) -> dict[str, Any]:
        result = original_begin(**kwargs)
        if result["outcome"] in {"started", "recovered_started"}:
            owner_started.set()
        elif result["outcome"] == "reused_in_progress":
            observer_started.set()
        return result

    def controlled_route(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal route_calls
        with route_lock:
            route_calls += 1
        if not release_route.wait(5):
            raise RuntimeError("test route release timed out")
        if owner_fails:
            raise RuntimeError("planned owner failure")
        return {
            "trace_id": "shared-attempt",
            "selected_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(store, "begin_preflight_attempt", observed_begin)
    monkeypatch.setattr(pipeline, "route", controlled_route)

    def invoke() -> Any:
        return run_preflight(
            store,
            session_id="session",
            user_message=message,
            host="codex",
            trace_id="shared-attempt",
            reservation_token=reservation["reservation_token"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(invoke)
        assert owner_started.wait(5)
        observer = executor.submit(invoke)
        assert observer_started.wait(5)
        release_route.set()
        if owner_fails:
            with pytest.raises(RuntimeError, match="planned owner failure"):
                owner.result(timeout=30)
            with pytest.raises(RuntimeError, match="became terminal"):
                observer.result(timeout=30)
        else:
            owner_result = owner.result(timeout=30)
            observer_result = observer.result(timeout=30)
            assert observer_result.as_dict() == owner_result.as_dict()

    assert route_calls == 1
    run = store.get_run("shared-attempt")
    if owner_fails:
        assert run["status"] == "preflight_failed"
        assert store.runtime_table_counts()["routing_decisions"] == 0
    else:
        assert run["status"] == "active"
        connection = store._connect()
        try:
            state = connection.execute(
                "SELECT preflight_state FROM runs WHERE trace_id = 'shared-attempt'"
            ).fetchone()["preflight_state"]
        finally:
            connection.close()
        assert state == "ready"
        assert store.runtime_table_counts()["routing_decisions"] == 1


def test_shared_attempt_observer_uses_one_bounded_query_with_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BusyAttempt:
        def __init__(self) -> None:
            self.queries = 0

        def observe_preflight_attempt(self, **_kwargs: Any) -> dict[str, Any]:
            self.queries += 1
            return {
                "run_status": "active",
                "preflight_state": "in_progress",
                "recipe": None,
            }

    clock = 0.0

    def advance(seconds: float) -> None:
        nonlocal clock
        clock += seconds

    monkeypatch.setattr(preflight_recipe, "monotonic", lambda: clock)
    monkeypatch.setattr(preflight_recipe, "sleep", advance)
    busy = BusyAttempt()

    with pytest.raises(RuntimeError, match="still in progress"):
        preflight_recipe._await_ready_result(
            busy,  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
            attempt_token="attempt",
            user_message="Review the runtime.",
            config=AgencyConfig(),
            pipeline=pipeline,
            timeout_seconds=0.8,
        )

    assert busy.queries <= 8


def test_expired_owner_is_recovered_and_stale_token_cannot_commit_or_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.preflight_recipe import _content_free_routing_recipe
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    session_id = "session"
    trace_id = "crashed-owner"
    message = "Audit the runtime lifecycle."
    reservation = store.reserve_session_turn(
        session_id=session_id,
        trace_id=trace_id,
        host="codex",
    )
    fingerprint = hashlib.sha256(message.encode()).hexdigest()
    crashed = store.begin_preflight_attempt(
        session_id=session_id,
        trace_id=trace_id,
        reservation_token=reservation["reservation_token"],
        request_fingerprint=fingerprint,
        request_kind="nontrivial",
        host="codex",
        lease_seconds=1,
    )
    assert crashed["outcome"] == "started"
    stale_token = crashed["attempt_token"]
    store.record_model_receipt(
        trace_id=trace_id,
        session_id=session_id,
        host="codex",
        source="stale-preflight",
    )
    store.record_skill_loaded(session_id, "stale-skill", trace_id=trace_id)
    store.record_specialist_loaded(session_id, "stale-specialist", trace_id=trace_id)
    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host="codex",
        work_unit_id="stale-unit",
        recommended_agent="stale-specialist",
        status="suggested",
        backend="preflight",
    )
    store.record_routing_decision(
        trace_id=trace_id,
        session_id=session_id,
        query_hash="d" * 64,
        context_fingerprint="e" * 64,
        decision={"status": "selected", "selected_ids": ["stale-specialist"]},
    )
    store.record_finalization(
        trace_id=trace_id,
        host="codex",
        action="continue",
        missing=["agency_header"],
    )
    store.record_finalization(
        trace_id=trace_id,
        host="codex",
        action="validation_continue",
        missing=["correlation"],
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET preflight_lease_expires_at = "
            "'2000-01-01T00:00:00.000000+00:00' WHERE trace_id = ?",
            (trace_id,),
        )
        connection.commit()
    finally:
        connection.close()

    routing = {
        "trace_id": trace_id,
        "selected_ids": [],
        "confidence": 0.0,
        "status": "abstained",
        "source": "test",
        "query_hash": fingerprint,
        "context_fingerprint": "c" * 64,
        "work_units": detect_work_units(message),
    }
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: routing)
    begin_outcomes: list[str] = []
    original_begin = store.begin_preflight_attempt

    def record_begin(**kwargs: Any) -> dict[str, Any]:
        result = original_begin(**kwargs)
        begin_outcomes.append(result["outcome"])
        return result

    monkeypatch.setattr(store, "begin_preflight_attempt", record_begin)
    recovered = run_preflight(
        store,
        session_id=session_id,
        user_message=message,
        host="codex",
        trace_id=trace_id,
        reservation_token=reservation["reservation_token"],
    )
    assert recovered.trace_id == trace_id
    assert begin_outcomes == ["recovered_started"]

    connection = store._connect()
    try:
        lifecycle = connection.execute(
            "SELECT status, preflight_state, preflight_attempt_token FROM runs WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
    finally:
        connection.close()
    recovered_token = str(lifecycle["preflight_attempt_token"])
    assert recovered_token and recovered_token != stale_token
    assert lifecycle["status"] == "active"
    assert lifecycle["preflight_state"] == "ready"
    ready_recipe = store.get_ready_preflight_result(
        session_id,
        trace_id,
        recovered_token,
    )
    assert ready_recipe is not None

    stale_commit = store.mark_preflight_ready(
        session_id=session_id,
        trace_id=trace_id,
        attempt_token=stale_token,
        recipe=ready_recipe,
        host="codex",
        routing_evidence=_content_free_routing_recipe(
            routing,
            trace_id=trace_id,
        ),
        suggestions=[],
        specialist_refs=[],
    )
    assert stale_commit == {"outcome": "cas_lost"}
    assert (
        store.fail_preflight_attempt(
            session_id=session_id,
            trace_id=trace_id,
            attempt_token=stale_token,
        )
        is False
    )
    assert store.get_run(trace_id)["status"] == "active"
    assert store.runtime_table_counts()["routing_decisions"] == 1
    assert store.get_model_receipt(trace_id) is None
    assert store.get_skills_for_trace(session_id, trace_id) == []
    assert store.get_specialists_for_trace(session_id, trace_id) == []
    assert store.get_delegations(trace_id) == []
    connection = store._connect()
    try:
        stale_finalizations = connection.execute(
            "SELECT COUNT(*) FROM finalization_events WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()[0]
    finally:
        connection.close()
    assert stale_finalizations == 0
    fresh_claim = store.claim_continuation(
        session_id=session_id,
        trace_id=trace_id,
        host="codex",
        response_hash="f" * 64,
        missing=["agency_header"],
    )
    assert fresh_claim["outcome"] == "claimed"


def test_expired_recovery_rolls_back_every_evidence_delete_when_update_fails(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    session_id = "session"
    trace_id = "rollback-recovery"
    fingerprint = hashlib.sha256(b"Audit the runtime lifecycle.").hexdigest()
    started = store.begin_preflight_attempt(
        session_id=session_id,
        trace_id=trace_id,
        request_fingerprint=fingerprint,
        request_kind="nontrivial",
        host="codex",
        lease_seconds=1,
    )
    assert started["outcome"] == "started"
    store.record_model_receipt(
        trace_id=trace_id,
        session_id=session_id,
        host="codex",
        source="stale-preflight",
    )
    store.record_skill_loaded(session_id, "stale-skill", trace_id=trace_id)
    store.record_specialist_loaded(session_id, "stale-specialist", trace_id=trace_id)
    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host="codex",
        work_unit_id="stale-unit",
        recommended_agent="stale-specialist",
        status="suggested",
        backend="preflight",
    )
    store.record_routing_decision(
        trace_id=trace_id,
        session_id=session_id,
        query_hash="d" * 64,
        context_fingerprint="e" * 64,
        decision={"status": "selected", "selected_ids": ["stale-specialist"]},
    )
    store.record_finalization(
        trace_id=trace_id,
        host="codex",
        action="continue",
        missing=["agency_header"],
    )
    store.record_finalization(
        trace_id=trace_id,
        host="codex",
        action="validation_continue",
        missing=["correlation"],
    )
    before = store.runtime_table_counts()

    connection = store._connect()
    try:
        connection.executescript(
            """
            UPDATE runs
            SET preflight_lease_expires_at = '2000-01-01T00:00:00.000000+00:00'
            WHERE trace_id = 'rollback-recovery';
            CREATE TRIGGER reject_expired_recovery
            BEFORE UPDATE OF preflight_attempt_token ON runs
            WHEN OLD.trace_id = 'rollback-recovery'
            BEGIN
                SELECT RAISE(ABORT, 'blocked recovery');
            END;
            """
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="blocked recovery"):
        store.begin_preflight_attempt(
            session_id=session_id,
            trace_id=trace_id,
            request_fingerprint=fingerprint,
            request_kind="nontrivial",
            host="codex",
            lease_seconds=1,
        )

    assert store.runtime_table_counts() == before
    receipt = store.get_model_receipt(trace_id)
    assert receipt is not None
    assert receipt["host"] == "codex"
    assert store.get_skills_for_trace(session_id, trace_id) == ["stale-skill"]
    assert store.get_specialists_for_trace(session_id, trace_id) == ["stale-specialist"]
    assert len(store.get_delegations(trace_id)) == 1
    connection = store._connect()
    try:
        preserved_finalizations = connection.execute(
            "SELECT action FROM finalization_events WHERE trace_id = ? ORDER BY action",
            (trace_id,),
        ).fetchall()
    finally:
        connection.close()
    assert [row["action"] for row in preserved_finalizations] == [
        "continue",
        "validation_continue",
    ]


def test_failure_first_prevents_late_ready_commit(
    tmp_path: Path,
) -> None:
    from agency_runtime.core.preflight_recipe import (
        PREFLIGHT_REPLAY_RECIPE_VERSION,
        _content_free_routing_recipe,
        _context_policy_fingerprint,
    )
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "agency.db")
    message = "Audit the runtime lifecycle."
    fingerprint = hashlib.sha256(message.encode()).hexdigest()
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="failure-wins",
        request_fingerprint=fingerprint,
        request_kind="nontrivial",
        host="codex",
        lease_seconds=60,
    )
    routing = {
        "trace_id": "failure-wins",
        "selected_ids": [],
        "confidence": 0.0,
        "status": "abstained",
        "source": "test",
        "query_hash": fingerprint,
        "context_fingerprint": "c" * 64,
        "work_units": detect_work_units(message),
    }
    routing_recipe = _content_free_routing_recipe(
        routing,
        trace_id="failure-wins",
    )
    recipe = {
        "recipe_version": PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": _context_policy_fingerprint(
            AgencyConfig(),
            pipeline,
            delivery_mode="isolated",
            context_limit=4_096,
        ),
        "session_id": "session",
        "trace_id": "failure-wins",
        "host": "codex",
        "delivery_mode": "isolated",
        "context_limit": 4_096,
        "routing": routing_recipe,
        "specialist_refs": [],
        "selection_refs": [],
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "trivial": False,
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test_fixture"],
            "state_revision": "f" * 64,
            "classifier_version": 1,
        },
        "resident_manager_binding": build_resident_manager_binding(
            session_id="session",
            host="codex",
            delivery_mode="request",
        ).as_dict(),
        "roster_size": 0,
        "roster_generation": 0,
    }

    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="failure-wins",
        attempt_token=started["attempt_token"],
    )
    assert store.mark_preflight_ready(
        session_id="session",
        trace_id="failure-wins",
        attempt_token=started["attempt_token"],
        recipe=recipe,
        host="codex",
        routing_evidence=routing_recipe,
        suggestions=[],
        specialist_refs=[],
    ) == {"outcome": "cas_lost"}
    assert store.get_run("failure-wins")["status"] == "preflight_failed"
    assert store.runtime_table_counts()["routing_decisions"] == 0


def test_store_clock_lease_exceeds_generated_hook_budget_by_write_margin(
    tmp_path: Path,
) -> None:
    from datetime import datetime

    from agency_runtime.core.installer_contracts import (
        HOOK_TIMEOUT_BUFFER_SECONDS,
        MAX_HOOK_TIMEOUT_SECONDS,
    )
    from agency_runtime.core.installer_payloads import hook_timeout_seconds

    store = Store(tmp_path / "agency.db")
    hook_budget = hook_timeout_seconds(AgencyConfig())
    assert 1 <= hook_budget <= MAX_HOOK_TIMEOUT_SECONDS
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="leased",
        request_fingerprint=hashlib.sha256(b"leased request").hexdigest(),
        request_kind="nontrivial",
        lease_seconds=hook_budget,
    )
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT last_activity_at, preflight_lease_expires_at "
            "FROM runs WHERE trace_id = 'leased'"
        ).fetchone()
    finally:
        connection.close()

    active_at = datetime.fromisoformat(str(row["last_activity_at"]).replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(
        str(row["preflight_lease_expires_at"]).replace("Z", "+00:00")
    )
    assert started["lease_expires_at"] == row["preflight_lease_expires_at"]
    # The lease and activity timestamp share one store-clock sample, so database
    # write duration cannot consume any part of the configured safety margin.
    assert (expires_at - active_at).total_seconds() == (hook_budget + HOOK_TIMEOUT_BUFFER_SECONDS)


def test_detector_bounds_large_input_dedupes_units_and_finishes_quickly() -> None:
    message = "\n".join(f"{index}. fix component {index}" for index in range(50_000))
    message += "\n999999. fix unreachable-sentinel"

    started = perf_counter()
    result = detect_work_units(message)
    elapsed = perf_counter() - started

    assert elapsed < 2.0
    assert result["count"] <= MAX_SUGGESTED_WORK_UNITS
    assert len(result["units"]) <= MAX_SUGGESTED_WORK_UNITS
    assert all(len(unit) <= MAX_WORK_UNIT_CHARS for unit in result["units"])
    assert "unreachable-sentinel" not in " ".join(result["units"])

    deduped = detect_work_units("fix the API; also fix the API; also fix the dashboard")
    assert deduped["units"] == ["fix the API", "fix the dashboard"]


def test_detector_does_not_split_a_noun_that_is_also_an_imperative() -> None:
    result = detect_work_units(
        "Review the authentication design, then document the deployment workflow."
    )

    assert result["units"] == [
        "Review the authentication design",
        "then document the deployment workflow.",
    ]
    assert result["source"] == "sequential_steps"
    assert result["delegate"] is False


def test_routing_and_context_enforce_fixed_projections() -> None:
    raw_message = "x" * (MAX_WORK_UNIT_INPUT_CHARS * 8)
    routed = pipeline.route("session", raw_message, [])
    bounded_message = raw_message[: pipeline.MAX_ROUTING_SIGNAL_CHARS]

    assert routed["query_hash"] == hashlib.sha256(bounded_message.encode()).hexdigest()

    hostile = {
        "selected_ids": [f"agent-{index}-" + "a" * 500 for index in range(100)],
        "confidence": float("nan"),
        "status": "status-" + "z" * 10_000,
        "source": "source-" + "z" * 10_000,
        "work_units": {
            "count": 10_000,
            "confidence": "high-" + "z" * 10_000,
            "source": "hostile-" + "z" * 10_000,
            "units": [f"work-item-{index}-" + "w" * 500 for index in range(100)],
            "delegate": True,
        },
    }
    context = pipeline.build_routing_context(hostile)

    assert len(context) <= pipeline.MAX_ROUTING_CONTEXT_CHARS
    assert "agent-15" in context
    assert "agent-16" not in context
    assert "work-item-15" in context
    assert "work-item-16" not in context
    assert (
        "Treat the current [AGENCY LOADED] capsule as the authoritative specialist context "
        "for this turn"
    ) in context


class _BatchStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record_suggested_delegations_batch(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return 10_000


def test_suggestion_recording_refuses_overflow_and_requires_correlation() -> None:
    store = _BatchStore()
    routing = {
        "trace_id": "turn",
        "selected_ids": ["agent-" + "a" * 1_000],
        "work_units": {
            "delegate": True,
            "count": 100,
            "units": [f"unit {index} " + "x" * 1_000 for index in range(100)],
        },
    }

    recorded = record_suggested_delegations(
        store,  # type: ignore[arg-type]
        session_id="session",
        host="codex",
        routing=routing,
    )

    assert recorded == 0
    assert store.calls == []

    assert (
        record_suggested_delegations(
            store,  # type: ignore[arg-type]
            session_id="",
            host="codex",
            routing=routing,
        )
        == 0
    )
    assert (
        record_suggested_delegations(
            store,  # type: ignore[arg-type]
            session_id="session",
            host="codex",
            routing={**routing, "trace_id": ""},
        )
        == 0
    )
    assert store.calls == []


def test_public_model_receipt_requires_explicit_session_and_trace(tmp_path: Path) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))

    with pytest.raises(TypeError):
        runtime.record_model_receipt()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="session_id and trace_id"):
        runtime.record_model_receipt(trace_id="", session_id="session")
    with pytest.raises(ValueError, match="session_id and trace_id"):
        runtime.record_model_receipt(trace_id="turn", session_id="")

    runtime.preflight(
        "session",
        "Record authoritative model telemetry for this turn.",
        trace_id="turn",
    )
    receipt_id = runtime.record_model_receipt(
        trace_id="turn",
        session_id="session",
        requested_model="task-general",
        resolved_provider="openai",
        resolved_model="gpt-test",
    )

    assert receipt_id
    assert runtime.store.get_model_receipt("turn")["session_id"] == "session"
    assert runtime.store.get_open_traces_for_session("session") == ["turn"]


def test_fresh_turn_builds_route_request_once_and_reuses_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PERF-01: a fresh UserPromptSubmit must build the routing request exactly
    once and reuse it via route(request=...). Previously the request was built
    twice (once for the context fingerprint, once inside route()).
    """

    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "implementer",
            "name": "Implementer",
            "description": "Implements bounded changes.",
            "prompt_body": "directive",
            "version": "1.0.0",
        }
    )

    build_calls = 0
    real_build = pipeline.build_route_request

    def counting_build(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return real_build(*args, **kwargs)

    # Stub route() so the test exercises only the request-build/reuse path,
    # not the full selector (which needs a configured provider).
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    captured_request_kwargs: list[dict[str, Any]] = []
    message = "perform the task"

    def stub_route(_session_id, _message, _catalog, **kwargs):
        captured_request_kwargs.append(dict(kwargs))
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(message),
        }

    monkeypatch.setattr(pipeline, "build_route_request", counting_build)
    monkeypatch.setattr(pipeline, "route", stub_route)

    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="adapter_preflight",
        session_id="dedup-session",
        trace_id="dedup-turn",
    )
    run_preflight(
        store,
        session_id="dedup-session",
        user_message="perform the task",
        host="codex",
        trace_id="dedup-turn",
        origin_receipt=origin_receipt,
    )

    # The request is built exactly once for the fresh turn.
    assert build_calls == 1, (
        f"expected build_route_request to fire once per fresh turn, got {build_calls}"
    )
    # And that single request is forwarded into route() via request=.
    assert any(kwargs.get("request") is not None for kwargs in captured_request_kwargs), (
        "route() must receive the pre-built request= kwarg"
    )
