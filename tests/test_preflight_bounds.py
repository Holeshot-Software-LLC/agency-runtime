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
    detect_work_units,
)
from agency_runtime.core.specialist_context import _prompt_context_lines
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import native_adapter_turn_origin
from agency_runtime.core.unit_assignment import work_unit_id_from_text


def _activate_test_specialist(store: Store, slug: str = "implementer") -> None:
    store._activate_prevalidated_agent(
        {
            "slug": slug,
            "name": slug.replace("-", " ").title(),
            "description": "Handles the bounded test request.",
            "prompt_body": "Complete only the assigned bounded test request.",
            "version": "1.0.0",
        }
    )


def _test_specialist_routing(
    user_message: str,
    trace_id: str,
    slug: str = "implementer",
) -> dict[str, Any]:
    from agency_runtime.core.workforce.routing_projection import (
        workforce_work_units_from_descriptors,
    )

    descriptors = [
        {
            "ordinal": 1,
            "artifact_kind": "review-report",
            "lifecycle_phase": "review",
            "authority": "review",
        }
    ]
    units = workforce_work_units_from_descriptors(user_message, descriptors)
    unit_id = work_unit_id_from_text(units[0])
    return {
        "trace_id": trace_id,
        "selected_ids": [slug],
        "confidence": 0.99,
        "status": "applied",
        "source": "test",
        "query_hash": hashlib.sha256(user_message.encode()).hexdigest(),
        "context_fingerprint": "c" * 64,
        "work_units": {
            "delegate": True,
            "count": 1,
            "units": units,
            "source": "verified-workforce-plan",
            "confidence": "high",
        },
        "workforce_unit_descriptors": descriptors,
        "workforce_unit_bindings": [
            {
                "source_unit_id": "unit-work",
                "work_unit_id": unit_id,
                "selected": [slug],
                "delivery": "delegate",
                "timing": "immediate",
                "depends_on": [],
                "parallelization": "sequential",
                "mutation_scope": "read_only",
                "artifact_kind": "review-report",
                "required_tools": [],
                "required_evidence": ["test evidence"],
                "confidence": 0.99,
            }
        ],
        "unit_assignment_agents": [
            {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "description": "Handles the bounded test request.",
                "capabilities": ["bounded test work"],
                "tags": ["test"],
                "required_tools": [],
                "evidence_requirements": ["test evidence"],
                "matched_work_unit_ids": [unit_id],
                "primary_work_unit_ids": [unit_id],
            }
        ],
    }


def _route_to_test_specialist(slug: str = "implementer"):
    def route(
        _session_id: str,
        user_message: str,
        _catalog: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return _test_specialist_routing(
            user_message,
            str(kwargs.get("trace_id") or "test-turn"),
            slug,
        )

    return route


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
    receipt = store.get_preflight_failure_receipt("session", "failed-turn")
    assert receipt is not None
    assert receipt["schema_version"] == "agency.preflight.failure.v3"
    assert receipt["stage"] == "routing"
    assert receipt["reason_code"] == "routing_failed"
    assert receipt["invariant_code"] == ""
    assert receipt["exception_category"] == "runtime_error"
    assert receipt["provider_attempts"] == []
    assert receipt["staffing_reason_codes"] == []
    assert receipt["hiring_reason_codes"] == []
    assert (
        store.get_completion_evidence_snapshot("session", "failed-turn")["preflight_failure"]
        == receipt
    )
    assert store.get_open_traces_for_session("session") == []


def test_preflight_failure_receipt_projects_provider_attempts_without_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    secret = "sk-secret-provider-value"
    response = "provider response must never be retained"
    prompt = "private prompt must never be retained"

    def failed_inference(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "selected_ids": [],
            "status": "inference_invalid",
            "source": "workforce_inference_failure",
            "provider_attempts": [
                {
                    "stage": "planner",
                    "provider_name": secret,
                    "provider_type": "cli",
                    "requested_model": "gpt-5.6-luna",
                    "model_group": "workforce",
                    "actual_model": "",
                    "model_receipt_source": "unavailable",
                    "status": "failed",
                    "reason_code": "provider_timeout",
                    "prompt": prompt,
                    "response": response,
                    "stderr": r"C:\private\provider.stderr",
                }
            ],
            "workforce_staffing": {
                "status": "abstained",
                "abstention_reasons": [
                    {
                        "code": "selected_agent_budget_exceeded",
                        "detail": response,
                    }
                ],
            },
            "hiring_events": [
                {
                    "reason_codes": ["gap_evidence_not_hireable"],
                    "notification": secret,
                }
            ],
        }

    monkeypatch.setattr(pipeline, "route", failed_inference)

    # ADR-0122 update: failed inference no longer blocks the parent model. The
    # turn fails open so the host can answer as a generalist, but the failure
    # receipt is still persisted for the dashboard and operator diagnosis.
    run_preflight(
        store,
        session_id="session",
        user_message="Audit and harden the runtime.",
        host="codex",
        trace_id="inference-failed",
    )

    receipt = store.get_preflight_failure_receipt("session", "inference-failed")
    assert receipt is not None
    assert receipt["stage"] == "routing"
    assert receipt["reason_code"] == "workforce_inference_failed"
    assert receipt["invariant_code"] == ""
    assert receipt["exception_category"] == "runtime_error"
    assert receipt["provider_attempts"] == [
        {
            "stage": "planner",
            "provider_name": receipt["provider_attempts"][0]["provider_name"],
            "provider_type": "cli",
            "requested_model": "gpt-5.6-luna",
            "model_group": "workforce",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "failed",
            "reason_code": "provider_timeout",
        }
    ]
    assert receipt["provider_attempts"][0]["provider_name"].startswith("sha256:")
    assert receipt["staffing_reason_codes"] == ["selected_agent_budget_exceeded"]
    assert receipt["hiring_reason_codes"] == ["gap_evidence_not_hireable"]
    connection = store._connect()
    try:
        durable = connection.execute(
            "SELECT provider_attempts, staffing_reason_codes, hiring_reason_codes "
            "FROM preflight_failure_receipts "
            "WHERE trace_id = 'inference-failed'"
        ).fetchone()
    finally:
        connection.close()
    durable_text = " ".join(
        str(durable[field])
        for field in (
            "provider_attempts",
            "staffing_reason_codes",
            "hiring_reason_codes",
        )
    )
    for forbidden in (secret, response, prompt, "provider.stderr"):
        assert forbidden not in durable_text
    [activity] = store.recent_dashboard_activity(limit=10)["preflight_failures"]
    assert activity["trace_id"] == "inference-failed"
    assert activity["stage"] == "routing"
    assert activity["reason_code"] == "workforce_inference_failed"
    assert activity["provider_attempts"] == receipt["provider_attempts"]
    assert activity["staffing_reason_codes"] == receipt["staffing_reason_codes"]
    assert activity["hiring_reason_codes"] == receipt["hiring_reason_codes"]


def test_schema_v39_backfills_and_immutably_scopes_legacy_preflight_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="legacy-failure",
        request_fingerprint=hashlib.sha256(b"legacy failure").hexdigest(),
        request_kind="nontrivial",
        host="codex",
    )
    assert store.fail_preflight_attempt(
        session_id="session",
        trace_id="legacy-failure",
        attempt_token=started["attempt_token"],
    )
    connection = store._connect()
    try:
        connection.execute(
            "DELETE FROM preflight_failure_receipts WHERE trace_id = 'legacy-failure'"
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (38)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    receipt = migrated.get_preflight_failure_receipt("session", "legacy-failure")
    assert receipt is not None
    assert receipt["stage"] == "lifecycle"
    assert receipt["reason_code"] == "preflight_lifecycle_failed"
    assert receipt["exception_category"] == "unavailable"
    connection = migrated._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE preflight_failure_receipts SET stage = 'routing' "
                "WHERE trace_id = 'legacy-failure'"
            )
    finally:
        connection.close()


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
    receipt = store.get_preflight_failure_receipt("session", "reserved")
    assert receipt is not None
    assert receipt["stage"] in {"routing_snapshot", "lifecycle"}
    assert receipt["exception_category"] == "runtime_error"
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
    monkeypatch.setattr(pipeline, "route", _route_to_test_specialist())
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


def test_preflight_persists_trivial_kind_and_bounds_parent_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    routing = {
        "trace_id": "bounded-turn",
        "selected_ids": [],
        "query_hash": hashlib.sha256(b"thanks").hexdigest(),
        "context_fingerprint": "c" * 64,
        "work_units": detect_work_units("thanks"),
    }
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: routing)

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
    assert len(result.context) <= 4_096
    assert "r" * 100 not in result.context
    assert "s" * 100 not in result.context
    # The header-block assertions that used to live here came from the isolated
    # context formatter. A trivial turn now carries the resident kernel and
    # nothing else, which is the point: Agency stays out of the way.
    assert result.loaded_specialists == ()
    assert result.selected_specialists == ()


def test_persistent_host_ceiling_is_the_general_preflight_ceiling() -> None:
    """A persistent parent carries the complete team, not a legacy smaller cap.

    The neighbouring ceiling tests all express their sizes as
    ``PERSISTENT_HOST_CONTEXT_CHARS + 1``, so they stay self-consistent no
    matter what that constant becomes and can never detect a regression in the
    constant itself -- a curated mutation lowering it to 8_192 survived every
    one of them. The invariant is the equality, so the equality is what has to
    be asserted.
    """

    from agency_runtime.core.preflight_recipe import (
        MAX_PREFLIGHT_CONTEXT_CHARS,
        PERSISTENT_HOST_CONTEXT_CHARS,
    )

    assert PERSISTENT_HOST_CONTEXT_CHARS == MAX_PREFLIGHT_CONTEXT_CHARS


def test_oversized_complete_context_fails_before_ready_is_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    store = Store(tmp_path / "oversized-context.db")
    _activate_test_specialist(store)
    monkeypatch.setattr(pipeline, "route", _route_to_test_specialist())
    monkeypatch.setattr(
        preflight_recipe,
        "_combine_context",
        lambda *_args, **_kwargs: "x" * (preflight_recipe.PERSISTENT_HOST_CONTEXT_CHARS + 1),
    )

    # An oversized character count trips the length ceiling first; a multibyte
    # payload under that limit trips the encoded-bytes ceiling. Either way the
    # turn must fail before anything is persisted ready.
    with pytest.raises(RuntimeError, match="delivery ceiling"):
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


def test_multibyte_complete_context_fails_before_ready_is_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    store = Store(tmp_path / "multibyte-context.db")
    _activate_test_specialist(store)
    monkeypatch.setattr(pipeline, "route", _route_to_test_specialist())
    multibyte_context = "🔥" * 12_000
    assert len(multibyte_context) < preflight_recipe.PERSISTENT_HOST_CONTEXT_CHARS
    assert (
        preflight_recipe._persistent_host_context_output_bytes(multibyte_context)
        > preflight_recipe.PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES
    )
    monkeypatch.setattr(
        preflight_recipe,
        "_combine_context",
        lambda *_args, **_kwargs: multibyte_context,
    )

    with pytest.raises(RuntimeError, match="encoded host delivery ceiling"):
        run_preflight(
            store,
            session_id="session",
            user_message="Review the runtime",
            host="codex",
            trace_id="multibyte-context",
        )

    run = store.get_run("multibyte-context")
    assert run is not None
    assert run["status"] == "preflight_failed"
    connection = store._connect()
    try:
        state = connection.execute(
            "SELECT preflight_state FROM runs WHERE trace_id = ?",
            ("multibyte-context",),
        ).fetchone()["preflight_state"]
    finally:
        connection.close()
    assert state != "ready"


def test_direct_preflight_loads_every_selected_specialist(
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

    # Two specialists were selected for a job that genuinely has two parts, so
    # both are handed over. This assertion previously proved the opposite,
    # because a hardcoded `selected[:1]` truncated every turn to one card.
    assert result.loaded_specialists == ("implementer", "independent-reviewer")
    assert "IMPLEMENTER-ONLY-DIRECTIVE" in result.context
    assert "REVIEWER-ONLY-DIRECTIVE" in result.context


def test_direct_preflight_filters_resident_steward_before_selecting_a_specialist(
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
            "selected_ids": ["agency-steward", "implementer"],
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


def test_direct_preflight_fails_open_on_resident_only_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ADR-0122 update: a resident-only fallback no longer blocks the parent
    # model. The host answers as a generalist and no specialist is bound.
    store = Store(tmp_path / "fallback.db")
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": ["agency-steward"],
            "confidence": 0.0,
            "status": "policy_fallback",
            "source": "policy_fallback",
            "query_hash": hashlib.sha256(b"Handle an unfamiliar request").hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units("Handle an unfamiliar request"),
        },
    )

    run_preflight(
        store,
        session_id="fallback-session",
        user_message="Handle an unfamiliar request",
        host="hermes",
        trace_id="fallback-turn",
    )

    assert store.get_specialists_for_session("fallback-session") == []


def test_ready_recipe_and_atomic_routing_evidence_never_persist_request_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
    secret = "ULTRA-SECRET-UNIT-TEXT"
    message = f"1. audit authentication {secret}\n2. harden dashboard transport {secret}"
    malicious_routing = {
        **_test_specialist_routing(message, "private-ready"),
        "provider": f"provider-{secret}",
        "error": f"error-{secret}",
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
    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
    message = "Review the runtime lifecycle."
    route_calls = 0

    def route_once(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal route_calls
        route_calls += 1
        return _test_specialist_routing(message, "ready-replay")

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
    reason="ADR-0087: the bind_workforce_snapshot stub returns an empty "
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
    # The specialist is handed to the caller, so the turn records it as loaded.
    assert first.loaded_specialists == ("code-reviewer",)
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
    # The durable recipe stays content-free: it pins identity, never a body.
    assert str(prompt_body) not in str(persisted)
    # The context is the opposite: handing the card to the caller IS the delivery.
    assert str(prompt_body) in first.context
    assert store.get_specialists_for_trace("session", "versioned-ready") == ["code-reviewer"]
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
    # Replay rebuilds the same delivered context from the pinned version, even
    # though the agent was deactivated between the two runs.
    assert str(prompt_body) in second.context


def test_ready_replay_fails_closed_under_changed_context_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
    monkeypatch.setattr(pipeline, "route", _route_to_test_specialist())
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
    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
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
        return _test_specialist_routing(message, "shared-attempt")

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
    store = Store(tmp_path / "agency.db")
    _activate_test_specialist(store)
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

    routing = _test_specialist_routing(message, trace_id)
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
        routing_evidence=ready_recipe["routing"],
        specialist_refs=ready_recipe["specialist_refs"],
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
    assert store.get_specialists_for_trace(session_id, trace_id) == ["implementer"]
    # A verified workforce route plans no delegation, so the recovered attempt
    # suggests none either. What this test is about is unchanged: the stale
    # token wrote nothing, and in particular no "stale-unit" row survived.
    delegations = store.get_delegations(trace_id)
    assert delegations == []
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
            delivery_mode="direct",
            context_limit=4_096,
        ),
        "session_id": "session",
        "trace_id": "failure-wins",
        "host": "codex",
        "delivery_mode": "direct",
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
        specialist_refs=[],
    ) == {"outcome": "cas_lost"}
    assert store.get_run("failure-wins")["status"] == "preflight_failed"
    assert store.get_preflight_failure_receipt("session", "failure-wins") is not None
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


class _BatchStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record_suggested_delegations_batch(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return 10_000


def test_public_model_receipt_requires_explicit_session_and_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = AgencyRuntime(str(tmp_path / "agency.db"))
    _activate_test_specialist(runtime.store)
    monkeypatch.setattr(pipeline, "route", _route_to_test_specialist())

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
    captured_request_kwargs: list[dict[str, Any]] = []
    message = "perform the task"

    def stub_route(_session_id, _message, _catalog, **kwargs):
        captured_request_kwargs.append(dict(kwargs))
        return _test_specialist_routing(message, "dedup-turn")

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


def test_recruiter_ranked_ids_stay_inside_the_receipt_bounded_json_depth() -> None:
    """A projected nomination failure must survive the reader that stores it.

    ``normalize_activity_rows`` decodes ``preflight_failure_receipts`` provider
    attempts at ``maximum_depth=4``. A nested ranked-id list pushes one attempt
    past that, and the decode failure is raised for the whole batch, so a single
    over-deep diagnostic row makes ``recent_runtime_activity`` unreadable and
    every caller sees "runtime evidence store is unavailable" -- which is how a
    live canary run was blocked on 2026-08-16.
    """

    from agency_runtime.core.bounded_json import safe_load_bounded_json
    from agency_runtime.core.preflight_failure import (
        MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
    )
    from agency_runtime.core.selector.receipt_projection import project_nomination_failures

    failures = project_nomination_failures(
        "workforce nomination failures: "
        "unit-server-code-review=staff_without_safe_team"
        "~code-reviewer~senior-secops-engineer~application-security-engineer"
    )
    assert failures == [
        {
            "unit_id": "unit-server-code-review",
            "reason_code": "staff_without_safe_team",
            "ranked_agent_ids": (
                "code-reviewer~senior-secops-engineer~application-security-engineer"
            ),
        }
    ]

    attempts = [
        {
            "provider_name": "claude-haiku",
            "provider_type": "cli",
            "reason_code": "structured_response_invalid",
            "nomination_failures": failures,
        }
    ]
    decoded = safe_load_bounded_json(
        json.dumps(attempts),
        maximum_bytes=MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
        maximum_depth=4,
        maximum_nodes=512,
    )
    assert decoded == attempts
