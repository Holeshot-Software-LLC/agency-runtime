from __future__ import annotations

import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
    CODEX_ACTIVATION_CANARY_PROMPT,
    CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
)
from agency_runtime.core.canary_proof import codex_activation_failures
from agency_runtime.core.codex_activation_verification import (
    CODEX_ACTIVATION_QUERY_HASH_ENV,
)
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import stub_inference_invoker, write_provider_config

_REQUEST = "Review this Python code for correctness"
_CHILD_TASK = "Review the exact child change."
_CHILD = "019fb000-1111-7222-8333-444455556666"
_LAUNCH = "launch-canary-child"
_NONCE = "nonce-canary-child"
_PROMPT = "You are the exact code-review specialist."
_CODEX_LINEAGE_PARENT = "01a041aa-830d-7a33-915b-fb8e8bf8e0f3"
_CODEX_LINEAGE_CHILD = "01a041ac-427c-7333-8616-12672552ce9b"
_CODEX_LINEAGE_WINDOW = "01a041ac-427c-7333-8616-12740adee42c"


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _native_child_decision(
    *,
    parent_session_id: str = "snapshot-parent",
    parent_trace_id: str = "snapshot-trace",
    child_id: str = _CHILD,
    launch_id: str = _LAUNCH,
    task: str = _CHILD_TASK,
    nonce: str = _NONCE,
) -> dict[str, object]:
    attempts = [
        {
            "provider_name": "selector",
            "provider_type": "openai",
            "requested_model": "gpt-test",
            "model_group": "",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "applied",
            "reason_code": "",
        }
    ]
    cards = [
        {
            "specialist_slug": "code-reviewer",
            "specialist_version": "v1",
            "specialist_prompt_hash": _digest(_PROMPT),
            "body_character_length": len(_PROMPT),
        }
    ]
    team_digest = _digest(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "codex",
        "parent_session_id": parent_session_id,
        "parent_trace_id": parent_trace_id,
        "launch_id": launch_id,
        "binding_kind": "child_id",
        "binding_id": child_id,
        "provider_attempts": attempts,
        "provider_receipt_digest": canonical_native_child_provider_receipt_digest(attempts),
        "task_sha256": _digest(task),
        "team_digest": team_digest,
        "candidate_digest": _digest("runtime"),
        "runtime_digest": _digest("runtime"),
        "install_id": "codex-install-1",
        "bundle_digest": _digest("bundle"),
        "issued_at": "2026-08-12T12:00:00Z",
        "expires_at": "2026-08-12T12:05:00Z",
        "nonce": nonce,
        "cards": cards,
    }


def _record_verified_native_child_delivery(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    child_id: str,
    nonce: str = _NONCE,
) -> None:
    """Persist the content-free route/receipt pair used by snapshot projection."""

    decision = _native_child_decision(
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        child_id=child_id,
        launch_id=child_id,
        task=CODEX_ACTIVATION_CANARY_WORK_UNIT,
        nonce=nonce,
    )
    context_fingerprint = _digest(f"context:{trace_id}")
    decision_id = store.record_routing_decision(
        trace_id=trace_id,
        session_id=session_id,
        query_hash=str(decision["task_sha256"]),
        context_fingerprint=context_fingerprint,
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": ["code-reviewer"],
            "semantic_ids": ["code-reviewer"],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": 1,
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": decision["task_sha256"],
            "query_hash": decision["task_sha256"],
            "context_fingerprint": context_fingerprint,
            "native_child_delivery": decision,
        },
    )
    store._record_native_child_delivery_verification(
        decision_id=decision_id,
        nonce=str(decision["nonce"]),
        artifact_digest=_digest(f"host-artifact:{child_id}"),
        host="codex",
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        launch_id=child_id,
        binding_kind="child_id",
        binding_id=child_id,
        child_id=child_id,
        cards=decision["cards"],
    )


def _assert_verified_reconciliation_projection(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
) -> None:
    """Prove the repaired link reaches the header and ready-receipt consumers."""

    from agency_runtime.core.header.contract import fill_header_fields

    snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
    ready = store.get_ready_routing_receipt(
        session_id,
        trace_id,
        evidence_revision=snapshot["evidence_revision"],
    )
    assert ready is not None
    [delegation] = snapshot["delegations"]
    assert delegation["retrieved_specialist_slug"] == "code-reviewer"
    fields = fill_header_fields(
        {},
        session_id,
        store,
        "task-general",
        trace_id,
        evidence_snapshot=snapshot,
    )
    assert fields["agencies_delegated"] == "code-reviewer via generic-worker/spawn_agent"


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield Store(tmp_path / "agency.db", config_path=config_path)
    finally:
        reset_config_cache()


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value} | {
            nested for item in value.values() for nested in _keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _keys(item)}
    return set()


def _codex_v1491_lineage_artifact(root: Path, *, cwd: Path) -> Path:
    artifact = (
        root / "2026" / "08" / "27" / f"rollout-2026-08-27T05-23-23-{_CODEX_LINEAGE_CHILD}.jsonl"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "timestamp": "2026-08-27T05:23:23.457Z",
                "type": "session_meta",
                "payload": {
                    "id": _CODEX_LINEAGE_CHILD,
                    "timestamp": "2026-08-27T05:23:23.389Z",
                    "session_id": _CODEX_LINEAGE_PARENT,
                    "parent_thread_id": _CODEX_LINEAGE_PARENT,
                    "source": {
                        "subagent": {
                            "thread_spawn": {
                                "parent_thread_id": _CODEX_LINEAGE_PARENT,
                                "depth": 1,
                                "agent_path": "/root/code_reviewer",
                                "agent_nickname": "Poincare",
                                "agent_role": None,
                            }
                        }
                    },
                    "originator": "codex_exec",
                    "cli_version": "0.149.1",
                    "cwd": str(cwd),
                    "model_provider": "openai",
                    "base_instructions": {
                        "text": "Exact supported Codex child instructions.",
                        "provenance": {"type": "model", "model": "gpt-5.6-sol"},
                    },
                    "agent_path": "/root/code_reviewer",
                    "agent_nickname": "Poincare",
                    "context_window": {"window_id": _CODEX_LINEAGE_WINDOW},
                    "history_mode": "paginated",
                    "thread_source": "subagent",
                    "multi_agent_version": "v2",
                },
                "ordinal": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact


def test_canary_activation_snapshot_projects_exact_preflight_failure(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline

    request = "Diagnose the exact preflight failure without retaining this request."
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TimeoutError("private provider timeout detail")
        ),
    )
    with pytest.raises(TimeoutError, match="private provider timeout detail"):
        run_preflight(
            store,
            session_id="failed-session",
            trace_id="failed-trace",
            user_message=request,
            host="codex",
            capability_receipt=native_adapter_capability_receipt(
                "codex",
                platform="windows" if os.name == "nt" else "linux",
                session_id="failed-session",
                trace_id="failed-trace",
            ),
        )

    query_hash = sha256(request.encode("utf-8")).hexdigest()
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["proven"] is False
    assert snapshot["reason"] == "preflight_failed"
    assert snapshot["session_id"] == "failed-session"
    assert snapshot["trace_id"] == "failed-trace"
    assert snapshot["cardinalities"]["routes"] == 0
    assert snapshot["cardinalities"]["runs"] == 1
    assert snapshot["cardinalities"]["preflight_failures"] == 1
    assert snapshot["run"]["status"] == "preflight_failed"
    assert snapshot["preflight_failure"]["stage"] == "routing"
    assert snapshot["preflight_failure"]["reason_code"] == "routing_failed"
    assert snapshot["preflight_failure"]["exception_category"] == "timeout"
    encoded = json.dumps(snapshot, sort_keys=True)
    assert request not in encoded
    assert "private provider timeout detail" not in encoded


def test_restricted_codex_parent_snapshot_resolves_only_the_exact_live_route(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-parent"
    trace_id = "restricted-trace"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'a' * 32}"
    result = run_preflight(
        store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
            available_tools=("repository-read", "native-delegation"),
        ),
    )

    snapshot = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )

    assert result.routing["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert snapshot is not None
    assert snapshot["proven"] is True
    assert snapshot["session_id"] == session_id
    assert snapshot["trace_id"] == trace_id
    assert snapshot["route"]["selected_ids"] == ["code-reviewer"]
    assert (
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id="other-trace",
        )
        is None
    )


def test_restricted_codex_backend_route_admits_only_the_exact_accepted_terminal_parent(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.child_delivery_evidence import (
        _restricted_codex_canary_route,
    )
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-terminal-parent"
    trace_id = "restricted-terminal-trace"
    child_id = "01a04324-a431-76d1-bdf6-2ddfe65db56b"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'1' * 32}"
    run_preflight(
        store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
            available_tools=("repository-read", "native-delegation"),
        ),
    )
    _record_verified_native_child_delivery(
        store,
        session_id=session_id,
        trace_id=trace_id,
        child_id=child_id,
    )

    assert (
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id=trace_id,
        )
        is not None
    )
    assert (
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id=trace_id,
            accepted_terminal=True,
        )
        is None
    )
    assert (
        _restricted_codex_canary_route(
            store,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
        )
        is not None
    )
    assert (
        _restricted_codex_canary_route(
            store,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            accepted_terminal_parent=True,
        )
        is None
    )
    with pytest.raises(ValueError, match="accepted_terminal must be a boolean"):
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id=trace_id,
            accepted_terminal=1,
        )

    revision = store.get_completion_evidence_snapshot(
        session_id,
        trace_id,
    )["evidence_revision"]
    committed = store.commit_terminal_finalization(
        session_id=session_id,
        trace_id=trace_id,
        host="codex",
        action="accept",
        response_hash="a" * 64,
        status="completed",
        expected_evidence_revision=revision,
    )

    assert committed["authoritative"] is True
    assert (
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id=trace_id,
        )
        is None
    )
    assert (
        _restricted_codex_canary_route(
            store,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
        )
        is None
    )
    terminal = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
        accepted_terminal=True,
    )
    terminal_route = _restricted_codex_canary_route(
        store,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        accepted_terminal_parent=True,
    )

    assert terminal is not None
    assert terminal["proven"] is True
    assert terminal["run"]["status"] == "completed"
    assert terminal["run"]["terminal_finalization_id"] == committed["event_id"]
    assert terminal["cardinalities"]["finalizations"] == 1
    assert terminal["finalizations"] == [
        {
            **terminal["finalizations"][0],
            "id": committed["event_id"],
            "trace_id": trace_id,
            "host": "codex",
            "action": "accept",
            "missing": [],
            "terminal_status": "completed",
        }
    ]
    assert terminal_route is not None
    assert terminal_route["binding_id"] == child_id


def test_restricted_codex_backend_terminal_parent_rejects_inexact_terminal_shapes(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.child_delivery_evidence import (
        _restricted_codex_canary_route,
    )
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )

    def prepared(label: str, nonce: str) -> tuple[Store, str, str]:
        session_id = f"restricted-{label}-parent"
        trace_id = f"restricted-{label}-trace"
        task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {nonce * 32}"
        run_preflight(
            store,
            session_id=session_id,
            trace_id=trace_id,
            user_message=task,
            host="codex",
            capability_receipt=native_adapter_capability_receipt(
                "codex",
                platform="windows" if os.name == "nt" else "linux",
                session_id=session_id,
                trace_id=trace_id,
                available_tools=("repository-read", "native-delegation"),
            ),
        )
        _record_verified_native_child_delivery(
            store,
            session_id=session_id,
            trace_id=trace_id,
            child_id={
                "closed": "01a04324-a432-76d1-bdf6-2ddfe65db56c",
                "rejected": "01a04324-a432-76d1-bdf6-2ddfe65db56d",
                "ambiguous": "01a04324-a432-76d1-bdf6-2ddfe65db56e",
                "pending": "01a04324-a432-76d1-bdf6-2ddfe65db56f",
                "missing": "01a04324-a432-76d1-bdf6-2ddfe65db570",
            }[label],
            nonce=f"nonce-{label}",
        )
        return store, session_id, trace_id

    seed_starter_roster(store)

    closed, closed_session, closed_trace = prepared("closed", "2")
    assert closed.close_turn_evidence(closed_session, closed_trace) == 1

    rejected, rejected_session, rejected_trace = prepared("rejected", "3")
    rejected_revision = rejected.get_completion_evidence_snapshot(
        rejected_session,
        rejected_trace,
    )["evidence_revision"]
    rejected_commit = rejected.commit_terminal_finalization(
        session_id=rejected_session,
        trace_id=rejected_trace,
        host="codex",
        action="response_invalid",
        response_hash="b" * 64,
        status="completed",
        expected_evidence_revision=rejected_revision,
    )
    assert rejected_commit["authoritative"] is True

    ambiguous, ambiguous_session, ambiguous_trace = prepared("ambiguous", "4")
    ambiguous.record_finalization(
        trace_id=ambiguous_trace,
        host="codex",
        action="continue",
        missing=["child_running"],
    )
    ambiguous_revision = ambiguous.get_completion_evidence_snapshot(
        ambiguous_session,
        ambiguous_trace,
    )["evidence_revision"]
    ambiguous_commit = ambiguous.commit_terminal_finalization(
        session_id=ambiguous_session,
        trace_id=ambiguous_trace,
        host="codex",
        action="accept",
        response_hash="c" * 64,
        status="completed",
        expected_evidence_revision=ambiguous_revision,
    )
    assert ambiguous_commit["authoritative"] is True

    pending, pending_session, pending_trace = prepared("pending", "5")
    pending_revision = pending.get_completion_evidence_snapshot(
        pending_session,
        pending_trace,
    )["evidence_revision"]
    pending_commit = pending.commit_terminal_finalization(
        session_id=pending_session,
        trace_id=pending_trace,
        host="codex",
        action="accept",
        response_hash="d" * 64,
        status="completed",
        expected_evidence_revision=pending_revision,
        pending_interaction_kind="authorization",
        pending_interaction_fingerprint="e" * 64,
    )
    assert pending_commit["authoritative"] is True

    missing, missing_session, missing_trace = prepared("missing", "6")
    missing_revision = missing.get_completion_evidence_snapshot(
        missing_session,
        missing_trace,
    )["evidence_revision"]
    missing_commit = missing.commit_terminal_finalization(
        session_id=missing_session,
        trace_id=missing_trace,
        host="codex",
        action="accept",
        response_hash="f" * 64,
        status="completed",
        expected_evidence_revision=missing_revision,
        missing=["evidence_verification"],
    )
    assert missing_commit["authoritative"] is True

    for candidate, session_id, trace_id in (
        (closed, closed_session, closed_trace),
        (rejected, rejected_session, rejected_trace),
        (ambiguous, ambiguous_session, ambiguous_trace),
        (pending, pending_session, pending_trace),
        (missing, missing_session, missing_trace),
    ):
        assert (
            candidate.get_codex_activation_canary_parent_snapshot(
                session_id=session_id,
                trace_id=trace_id,
                accepted_terminal=True,
            )
            is None
        )
        assert (
            _restricted_codex_canary_route(
                candidate,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                accepted_terminal_parent=True,
            )
            is None
        )


def test_restricted_codex_collectors_keep_live_and_terminal_authority_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import child_delivery_evidence, codex_activation_verification

    observed: list[bool] = []

    def verify(*_args: object, **kwargs: object) -> None:
        observed.append(bool(kwargs.get("accepted_terminal_parent", False)))
        return None

    monkeypatch.setattr(
        child_delivery_evidence,
        "_verify_restricted_codex_canary_child_delivery",
        verify,
    )
    monkeypatch.setattr(
        codex_activation_verification,
        "is_restricted_codex_activation_canary_environment",
        lambda _environment: True,
    )

    assert (
        child_delivery_evidence._collect_restricted_codex_canary_child_delivery(
            object(),
            parent_session_id="collector-parent",
            parent_trace_id="collector-trace",
        )
        is None
    )
    collection = child_delivery_evidence._collect_restricted_codex_canary_host_delivery(
        object(),
        parent_session_id="collector-parent",
        parent_trace_id="collector-trace",
        started_at_ns=1,
        finished_at_ns=2,
        root=tmp_path,
    )

    assert collection.reason == "verification_refused"
    assert observed == [False, True]


def test_restricted_codex_child_hook_resolves_one_host_lineage_bound_parent(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core import child_delivery_evidence
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'d' * 32}"
    query_hash = sha256(task.encode("utf-8")).hexdigest()
    monkeypatch.setenv(CODEX_ACTIVATION_QUERY_HASH_ENV, query_hash)
    root = tmp_path / "codex-sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_lineage_artifact(root, cwd=cwd)
    monkeypatch.setattr(
        child_delivery_evidence,
        "default_child_artifact_root",
        lambda host: root,
    )
    monkeypatch.setattr(
        child_delivery_evidence,
        "storage_artifact_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        child_delivery_evidence,
        "storage_file_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    run_preflight(
        store,
        session_id=_CODEX_LINEAGE_PARENT,
        trace_id="digest-trace",
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=_CODEX_LINEAGE_PARENT,
            trace_id="digest-trace",
            available_tools=("repository-read", "native-delegation"),
        ),
    )
    bridge = HookBridge("codex", store=store, _master={"enabled": True})
    payload = {
        "hook_event_name": "SubagentStart",
        # Codex 0.149.1 keeps the root session in ``session_id`` and identifies
        # the spawned child thread separately in ``agent_id``.
        "session_id": _CODEX_LINEAGE_PARENT,
        "agent_id": _CODEX_LINEAGE_CHILD,
        "agent_type": "default",
        "cwd": str(cwd),
        "transcript_path": str(artifact),
    }

    assert bridge._restricted_codex_activation_child_parent_scope(payload) == (
        _CODEX_LINEAGE_PARENT,
        "digest-trace",
    )
    assert bridge._restricted_codex_activation_child_parent_scope(
        {
            **payload,
            "hook_event_name": "SubagentStop",
            "agent_transcript_path": str(artifact),
        }
    ) == (_CODEX_LINEAGE_PARENT, "digest-trace")
    assert (
        bridge._restricted_codex_activation_child_parent_scope(
            {**payload, "hook_event_name": "SubagentStop"}
        )
        is None
    )
    assert (
        bridge._restricted_codex_activation_child_parent_scope(
            {**payload, "session_id": _CODEX_LINEAGE_WINDOW}
        )
        is None
    )
    monkeypatch.setenv(CODEX_ACTIVATION_QUERY_HASH_ENV, "e" * 64)
    assert bridge._restricted_codex_activation_child_parent_scope(payload) is None

    monkeypatch.delenv(CODEX_ACTIVATION_QUERY_HASH_ENV)
    assert bridge._restricted_codex_activation_child_parent_scope(payload) == (
        _CODEX_LINEAGE_PARENT,
        "digest-trace",
    )
    monkeypatch.delenv("AGENCY_CANARY_MODE")
    assert bridge._restricted_codex_activation_child_parent_scope(payload) is None
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv(CODEX_ACTIVATION_QUERY_HASH_ENV, query_hash)

    run_preflight(
        store,
        session_id="01a041aa-830e-7a33-915b-fb8e8bf8e0f3",
        trace_id="duplicate-trace",
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id="01a041aa-830e-7a33-915b-fb8e8bf8e0f3",
            trace_id="duplicate-trace",
            available_tools=("repository-read", "native-delegation"),
        ),
    )
    ambiguous = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert ambiguous["reason"] == "route_ambiguous"
    assert bridge._restricted_codex_activation_child_parent_scope(payload) == (
        _CODEX_LINEAGE_PARENT,
        "digest-trace",
    )

    run_preflight(
        store,
        session_id=_CODEX_LINEAGE_PARENT,
        trace_id="second-parent-trace",
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=_CODEX_LINEAGE_PARENT,
            trace_id="second-parent-trace",
            available_tools=("repository-read", "native-delegation"),
        ),
    )
    assert bridge._restricted_codex_activation_child_parent_scope(payload) is None
    assert store.close_turn_evidence(_CODEX_LINEAGE_PARENT, "second-parent-trace") == 1
    assert store.close_turn_evidence(_CODEX_LINEAGE_PARENT, "digest-trace") == 1
    assert bridge._restricted_codex_activation_child_parent_scope(payload) is None


def test_restricted_codex_child_lineage_rejects_a_terminal_parent(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core import child_delivery_evidence
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'f' * 32}"
    query_hash = sha256(task.encode("utf-8")).hexdigest()
    monkeypatch.setenv(CODEX_ACTIVATION_QUERY_HASH_ENV, query_hash)
    root = tmp_path / "codex-sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_lineage_artifact(root, cwd=cwd)
    monkeypatch.setattr(child_delivery_evidence, "default_child_artifact_root", lambda host: root)
    monkeypatch.setattr(
        child_delivery_evidence,
        "storage_artifact_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        child_delivery_evidence,
        "storage_file_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    run_preflight(
        store,
        session_id=_CODEX_LINEAGE_PARENT,
        trace_id="terminal-trace",
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=_CODEX_LINEAGE_PARENT,
            trace_id="terminal-trace",
            available_tools=("repository-read", "native-delegation"),
        ),
    )
    bridge = HookBridge("codex", store=store, _master={"enabled": True})
    payload = {
        "hook_event_name": "SubagentStart",
        "session_id": _CODEX_LINEAGE_PARENT,
        "agent_id": _CODEX_LINEAGE_CHILD,
        "cwd": str(cwd),
        "transcript_path": str(artifact),
    }
    assert bridge._restricted_codex_activation_child_parent_scope(payload) == (
        _CODEX_LINEAGE_PARENT,
        "terminal-trace",
    )
    assert store.close_turn_evidence(_CODEX_LINEAGE_PARENT, "terminal-trace") == 1
    assert bridge._restricted_codex_activation_child_parent_scope(payload) is None


def test_restricted_codex_user_prompt_injects_the_exact_native_plan(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-plan-parent"
    trace_id = "restricted-plan-trace"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'b' * 32}"

    output = HookBridge(
        "codex",
        store=store,
        _master={"enabled": True},
    ).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": trace_id,
            "model": "gpt-5.6-codex",
            "prompt": task,
        }
    )

    context = output["hookSpecificOutput"]["additionalContext"]
    assert context.count("[AGENCY DELEGATION PLAN]") == 1
    plan = context.split("[AGENCY DELEGATION PLAN]", 1)[1]
    assert '"specialist":"code-reviewer"' in plan
    assert f'"native_task_name":"{CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME}"' in plan
    assert json.dumps(CODEX_ACTIVATION_CANARY_WORK_UNIT) in plan
    assert '"work_unit_id":"unit-05d45f7553"' in plan
    snapshot = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )
    assert snapshot is not None
    assert snapshot["route"]["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE


def test_restricted_codex_opaque_spawn_preserves_the_proven_parent_route(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The v6 child hook, not opaque PreToolUse text, owns canary staffing."""

    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-opaque-parent"
    trace_id = "restricted-opaque-trace"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'c' * 32}"
    bridge = HookBridge("codex", store=store, _master={"enabled": True})
    bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": trace_id,
            "model": "gpt-5.6-codex",
            "prompt": task,
        }
    )
    before = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )
    assert before is not None
    assert before["proven"] is True

    response = HookBridge(
        "codex",
        store=store,
        _master={"enabled": True},
    ).handle(
        {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "turn_id": trace_id,
            "tool_use_id": "call-restricted-opaque",
            "tool_name": "collaborationspawn_agent",
            "transcript_path": str(tmp_path / "missing-rollout.jsonl"),
            "tool_input": {
                "fork_turns": "none",
                "message": "gAAAAA" + "A" * 80,
                "task_name": CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
            },
        }
    )

    after = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )
    assert response == {}
    assert after is not None
    assert after["proven"] is True
    assert after["route"]["id"] == before["route"]["id"]
    connection = store._connect()
    try:
        sources = [
            str(row["source"])
            for row in connection.execute(
                "SELECT source FROM routing_decisions WHERE session_id = ? "
                "AND trace_id = ? ORDER BY created_at, rowid",
                (session_id, trace_id),
            ).fetchall()
        ]
    finally:
        connection.close()
    assert sources == [CODEX_ACTIVATION_CANARY_ROUTE_SOURCE]

    # The exception is exact: another opaque native spawn in the same managed
    # parent remains an ordinary unsupported channel and keeps its diagnostic.
    assert (
        bridge.handle(
            {
                "hook_event_name": "PreToolUse",
                "session_id": session_id,
                "turn_id": trace_id,
                "tool_use_id": "call-restricted-ordinary",
                "tool_name": "collaborationspawn_agent",
                "transcript_path": str(tmp_path / "missing-ordinary-rollout.jsonl"),
                "tool_input": {
                    "fork_turns": "none",
                    "message": "gAAAAA" + "D" * 80,
                    "task_name": "ordinary_worker",
                },
            }
        )
        == {}
    )
    connection = store._connect()
    try:
        sources = [
            str(row["source"])
            for row in connection.execute(
                "SELECT source FROM routing_decisions WHERE session_id = ? "
                "AND trace_id = ? ORDER BY created_at, rowid",
                (session_id, trace_id),
            ).fetchall()
        ]
    finally:
        connection.close()
    assert sources == [
        CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
        "native_child_inference_failure",
    ]


@pytest.mark.parametrize(
    "overlap_state",
    ["none", "unbound", "conflicting-dispatch"],
    ids=["pending-rekey", "concurrent-real-merge", "conflicting-real-rejected"],
)
def test_restricted_codex_post_tool_first_promotes_the_pending_dispatch(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    overlap_state: str,
) -> None:
    """ADR-0144 joins the real child even when PostToolUse arrives first."""

    from agency_runtime.adapters import hooks
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.native_child_staffing import NativeChildStaffingResult
    from agency_runtime.core.unit_assignment import work_unit_id_from_text
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-post-first-parent"
    trace_id = "restricted-post-first-trace"
    tool_use_id = "call-restricted-post-first"
    child_id = "01a04313-bcd6-79b1-b304-f37769d1872e"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'e' * 32}"
    tool_input = {
        "fork_turns": "none",
        "message": "gAAAAA" + "B" * 80,
        "task_name": CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
    }
    bridge = HookBridge("codex", store=store, _master={"enabled": True})
    bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": trace_id,
            "model": "gpt-5.6-codex",
            "prompt": task,
        }
    )

    post_payload = {
        "hook_event_name": "PostToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "tool_use_id": tool_use_id,
        "tool_name": "collaborationspawn_agent",
        "tool_input": tool_input,
        "tool_response": json.dumps({"task_name": "/root/code_reviewer"}),
    }
    bridge.handle(post_payload)

    unit = work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT)
    pending = store.get_native_child_run(
        host="codex",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id="task:code_reviewer",
        native_run_id="codex-task:code_reviewer",
    )
    assert pending is not None
    assert pending["execution_tool_use_id"] == tool_use_id
    assert pending["execution_dispatched_at"]

    def staff(*_args: object, **_kwargs: object) -> NativeChildStaffingResult:
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task="[AGENCY INFERENCE TEAM v6]\nexact delivery",
            decision_id="decision-post-first",
            selected_ids=("code-reviewer",),
        )

    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_staffing.staff_native_child",
        staff,
    )
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence._restricted_codex_canary_route",
        lambda *_args, **_kwargs: {
            "decision_id": "decision-post-first",
            "binding_id": child_id,
            "launch_id": child_id,
        },
    )

    # Model the narrow callback overlap where SubagentStart has recorded the
    # real worker after PostToolUse retained the synthetic pending dispatch,
    # but before either callback performed the final promotion.
    if overlap_state != "none":
        overlapping_real = store.record_native_child_started(
            host="codex",
            backend="spawn_agent",
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=unit,
            worker_id=child_id,
            native_run_id=f"codex-agent:{child_id}",
        )
        assert overlapping_real["delegation_event_id"] is None
    if overlap_state == "conflicting-dispatch":
        assert store.bind_native_child_launch(
            host="codex",
            session_id=session_id,
            trace_id=trace_id,
            worker_id=child_id,
            native_run_id=f"codex-agent:{child_id}",
            launch_id="call-conflicting-real",
        )

    delivered = bridge._staff_restricted_codex_activation_child(
        session_id=session_id,
        trace_id=trace_id,
        identity=hooks._native_child_identity("codex", child_id),
    )

    if overlap_state == "conflicting-dispatch":
        assert delivered == ""
        [unpromoted] = store.get_delegations(trace_id)
        assert unpromoted["executed_worker_id"] == "task:code_reviewer"
        assert unpromoted["native_run_id"] == "codex-task:code_reviewer"
        assert (
            store.get_native_child_run(
                host="codex",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=unit,
                worker_id="task:code_reviewer",
                native_run_id="codex-task:code_reviewer",
            )["execution_tool_use_id"]
            == tool_use_id
        )
        assert (
            store.get_native_child_run(
                host="codex",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=unit,
                worker_id=child_id,
                native_run_id=f"codex-agent:{child_id}",
            )["execution_tool_use_id"]
            == "call-conflicting-real"
        )
        return

    assert delivered == "[AGENCY INFERENCE TEAM v6]\nexact delivery"
    [delegation] = store.get_delegations(trace_id)
    assert delegation["work_unit_id"] == unit
    assert delegation["recommended_agent"] == "code-reviewer"
    assert delegation["executed_worker_id"] == child_id
    assert delegation["native_run_id"] == f"codex-agent:{child_id}"
    promoted = store.get_native_child_run(
        host="codex",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=child_id,
        native_run_id=f"codex-agent:{child_id}",
    )
    assert promoted is not None
    assert promoted["delegation_event_id"] == delegation["id"]
    assert promoted["execution_tool_use_id"] == tool_use_id
    assert promoted["execution_dispatched_at"]
    assert (
        bridge._staff_restricted_codex_activation_child(
            session_id=session_id,
            trace_id=trace_id,
            identity=hooks._native_child_identity("codex", child_id),
        )
        == "[AGENCY INFERENCE TEAM v6]\nexact delivery"
    )
    assert len(store.get_delegations(trace_id)) == 1
    bridge.handle(post_payload)
    assert len(store.get_delegations(trace_id)) == 1
    assert (
        store.get_native_child_run(
            host="codex",
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=unit,
            worker_id="task:code_reviewer",
            native_run_id="codex-task:code_reviewer",
        )
        is None
    )
    store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=child_id,
        native_run_id=f"codex-agent:{child_id}",
        outcome="ok",
    )
    _record_verified_native_child_delivery(
        store,
        session_id=session_id,
        trace_id=trace_id,
        child_id=child_id,
    )
    _assert_verified_reconciliation_projection(
        store,
        session_id=session_id,
        trace_id=trace_id,
    )


def test_restricted_codex_subagent_start_first_claims_at_post_tool(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The opposite ADR-0144 callback order keeps the direct real-child path."""

    from agency_runtime.adapters import hooks
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.native_child_staffing import NativeChildStaffingResult
    from agency_runtime.core.unit_assignment import work_unit_id_from_text
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-start-first-parent"
    trace_id = "restricted-start-first-trace"
    tool_use_id = "call-restricted-start-first"
    child_id = "01a04315-bcd6-79b1-b304-f37769d1872e"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'f' * 32}"
    tool_input = {
        "fork_turns": "none",
        "message": "gAAAAA" + "C" * 80,
        "task_name": CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
    }
    bridge = HookBridge("codex", store=store, _master={"enabled": True})
    bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": trace_id,
            "model": "gpt-5.6-codex",
            "prompt": task,
        }
    )

    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_staffing.staff_native_child",
        lambda *_args, **_kwargs: NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task="[AGENCY INFERENCE TEAM v6]\nexact delivery",
            decision_id="decision-start-first",
            selected_ids=("code-reviewer",),
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence._restricted_codex_canary_route",
        lambda *_args, **_kwargs: {
            "decision_id": "decision-start-first",
            "binding_id": child_id,
            "launch_id": child_id,
        },
    )
    identity = hooks._native_child_identity("codex", child_id)

    assert (
        bridge._staff_restricted_codex_activation_child(
            session_id=session_id,
            trace_id=trace_id,
            identity=identity,
        )
        == "[AGENCY INFERENCE TEAM v6]\nexact delivery"
    )
    unit = work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT)
    before_post = store.get_native_child_run(
        host="codex",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=child_id,
        native_run_id=f"codex-agent:{child_id}",
    )
    assert before_post is not None
    assert before_post["delegation_event_id"] is None
    assert before_post["execution_tool_use_id"] == ""
    store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=child_id,
        native_run_id=f"codex-agent:{child_id}",
        outcome="ok",
    )

    post_payload = {
        "hook_event_name": "PostToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "tool_use_id": tool_use_id,
        "tool_name": "collaborationspawn_agent",
        "tool_input": tool_input,
        "tool_response": json.dumps({"task_name": "/root/code_reviewer"}),
    }
    bridge.handle(post_payload)

    [delegation] = store.get_delegations(trace_id)
    assert delegation["work_unit_id"] == unit
    assert delegation["executed_worker_id"] == child_id
    assert delegation["native_run_id"] == f"codex-agent:{child_id}"
    claimed = store.get_native_child_run(
        host="codex",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=child_id,
        native_run_id=f"codex-agent:{child_id}",
    )
    assert claimed is not None
    assert claimed["delegation_event_id"] == delegation["id"]
    assert claimed["execution_tool_use_id"] == tool_use_id
    assert claimed["execution_dispatched_at"]
    assert claimed["ended_at"]
    assert delegation["status"] == "completed"
    bridge.handle(post_payload)
    [replayed] = store.get_delegations(trace_id)
    assert replayed["id"] == delegation["id"]
    assert replayed["status"] == "completed"
    _record_verified_native_child_delivery(
        store,
        session_id=session_id,
        trace_id=trace_id,
        child_id=child_id,
    )
    _assert_verified_reconciliation_projection(
        store,
        session_id=session_id,
        trace_id=trace_id,
    )


def test_store_receipt_remains_diagnostic_without_host_artifact_proof(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    preflight = run_preflight(
        store,
        session_id="snapshot-parent",
        trace_id="snapshot-trace",
        user_message=_REQUEST,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id="snapshot-parent",
            trace_id="snapshot-trace",
        ),
    )
    decision = _native_child_decision()
    decision_id = store.record_routing_decision(
        trace_id="snapshot-trace",
        session_id="snapshot-parent",
        query_hash=str(decision["task_sha256"]),
        context_fingerprint=_digest("context"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": ["code-reviewer"],
            "semantic_ids": ["code-reviewer"],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": 1,
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": decision["task_sha256"],
            "query_hash": decision["task_sha256"],
            "context_fingerprint": _digest("context"),
            "native_child_delivery": decision,
        },
    )
    query_hash = str(preflight.routing["query_hash"])

    missing = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert missing["route"]["id"] != decision_id
    assert missing["cardinalities"]["native_child_routes"] == 1
    assert missing["cardinalities"]["native_child_deliveries"] == 0
    assert missing["native_child_route"] is None
    assert missing["native_child_delivery"] is None
    assert missing["host_child_delivery"] is None

    # Codex 0.147 cannot mint this receipt through the live artifact verifier;
    # seed the private Store boundary and prove that it remains diagnostic.
    receipt = store._record_native_child_delivery_verification(
        decision_id=decision_id,
        nonce=_NONCE,
        artifact_digest=_digest("host-artifact"),
        host="codex",
        parent_session_id="snapshot-parent",
        parent_trace_id="snapshot-trace",
        launch_id=_LAUNCH,
        binding_kind="child_id",
        binding_id=_CHILD,
        child_id=_CHILD,
        cards=decision["cards"],
    )
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["route"]["id"] != snapshot["native_child_route"]["decision_id"]
    assert snapshot["native_child_route"]["decision_id"] == decision_id
    assert snapshot["native_child_delivery"] == receipt
    assert snapshot["host_child_delivery"] is None
    assert snapshot["cardinalities"]["native_child_routes"] == 1
    assert snapshot["cardinalities"]["native_child_deliveries"] == 1

    response = "Agency/Agencies loaded: code-reviewer"
    response_hash = _digest(response)
    canary_snapshot = deepcopy(snapshot)
    canary_snapshot["run"].update(
        status="completed",
        ended_at="2026-08-12T12:00:02Z",
        terminal_finalization_id="final-1",
    )
    canary_snapshot["worker_runs"] = [
        {
            "worker_id": _CHILD,
            "native_run_id": f"codex-agent:{_CHILD}",
            "backend": "spawn_agent",
            "host": "codex",
            "started_at": "2026-08-12T12:00:00Z",
            "ended_at": "2026-08-12T12:00:02Z",
        }
    ]
    canary_snapshot["finalizations"] = [
        {
            "id": "final-1",
            "action": "accept",
            "terminal_status": "completed",
            "response_hash": response_hash,
        }
    ]
    canary_snapshot["cardinalities"].update(worker_runs=1, finalizations=1)
    result = {
        "collaboration": {
            "unexpected_item_count": 0,
            "unexpected_item_types": [],
            "calls": [
                {
                    "tool": "spawn_agent",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "snapshot-parent",
                    "receiver_thread_ids": [_CHILD],
                    "execution_delivery": {"native_task_name": "agency_task"},
                },
                {
                    "tool": "wait",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "snapshot-parent",
                    "receiver_thread_ids": [_CHILD],
                    "agents_states": {_CHILD: "completed"},
                },
            ],
        }
    }

    assert codex_activation_failures(
        result=result,
        evidence=canary_snapshot,
        response_hash=response_hash,
    ) == ("verified host-authored Codex child card delivery was not proven",)

    second = deepcopy(decision)
    second["launch_id"] = "launch-second-child"
    second["nonce"] = "nonce-second-child"
    second["binding_id"] = "second-child"
    store.record_routing_decision(
        trace_id="snapshot-trace",
        session_id="snapshot-parent",
        query_hash=str(second["task_sha256"]),
        context_fingerprint=_digest("second-context"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": ["code-reviewer"],
            "semantic_ids": ["code-reviewer"],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": 1,
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": second["task_sha256"],
            "query_hash": second["task_sha256"],
            "context_fingerprint": _digest("second-context"),
            "native_child_delivery": second,
        },
    )
    ambiguous = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert ambiguous["cardinalities"]["native_child_routes"] == 2
    assert ambiguous["cardinalities"]["native_child_deliveries"] == 1
    assert ambiguous["native_child_route"] is None
    assert ambiguous["native_child_delivery"] is None
    assert ambiguous["host_child_delivery"] is None
