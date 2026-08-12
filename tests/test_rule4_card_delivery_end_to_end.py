"""Agency-side Rule-4 chain against the real Store and bundled roster.

This is a source-level simulation, not live host proof. It proves that one
validated inference decision becomes one exact multi-card launch envelope and
that only a separately parsed host artifact plus atomic Store consumption can
upgrade the attempt to verified delivery. Installed/live matrix cells still
require artifacts written by the actual native host.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import native_child_staffing
from agency_runtime.core.child_delivery_evidence import (
    _begin_private_host_artifact_collection,
    _collect_private_host_child_delivery,
    _consume_verified_host_child_delivery,
    _finish_private_host_invocation,
    _start_private_host_invocation,
    child_delivery_evidence,
)
from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.native_child_install_identity import NativeChildInstallIdentity
from agency_runtime.core.native_child_prompt_delivery import parse_inference_team_delivery
from agency_runtime.core.private_paths import _private_temporary_directory_lease
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.store.sqlite import Store

SESSION = "rule4-session"
TRACE = "rule4-parent-trace"
CHILD = "rule4-child-one"
TASK = "Design the backend architecture and review the implementation."
SELECTED = ("software-architect", "code-reviewer")
AVAILABLE_TOOLS: frozenset[str] = frozenset()


@pytest.fixture(scope="module")
def _seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("rule4-inference-seed") / "seed.db"
    store = Store(path)
    for agent in bundled_roster():
        store._activate_prevalidated_agent(agent)
    return path


@pytest.fixture
def store(_seeded_db: Path, tmp_path: Path) -> Store:
    target = tmp_path / "agency.db"
    shutil.copyfile(_seeded_db, target)
    result = Store(target)
    result.create_run(
        session_id=SESSION,
        trace_id=TRACE,
        host="claude",
        user_message="Parent request",
    )
    return result


@pytest.fixture
def collector_lease():
    with _private_temporary_directory_lease(prefix="rule4-proof-test") as lease:
        yield lease


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _install() -> NativeChildInstallIdentity:
    runtime = _digest("runtime")
    return NativeChildInstallIdentity(
        host="claude",
        plugin_version="test",
        install_id="install-rule4",
        bundle_digest=_digest("bundle"),
        running_runtime_digest=runtime,
        candidate_digest=runtime,
    )


def _judge_result() -> dict[str, Any]:
    return {
        "selected_ids": list(SELECTED),
        "confidence": 0.99,
        "latency_ms": 12,
        "status": "applied",
        "inference_mode": "inferred",
        "inference_configured": True,
        "inference_attempted": True,
        "provider_name": "primary",
        "candidate_count": 20,
        "top_score": 0.9,
        "provider_attempts": [
            {
                "provider_name": "primary",
                "provider_type": "litellm",
                "requested_model": "task-general",
                "model_group": "production-router",
                "actual_model": "gpt-5.6",
                "model_receipt_source": "litellm",
                "status": "applied",
                "reason": "",
            }
        ],
    }


def _staff(monkeypatch: pytest.MonkeyPatch, store: Store):
    issued = datetime.now(timezone.utc).replace(microsecond=0)
    monkeypatch.setattr(
        native_child_staffing,
        "query_judge",
        lambda *_args, **_kwargs: _judge_result(),
    )
    monkeypatch.setattr(native_child_staffing, "_utc_now", lambda: issued)
    monkeypatch.setattr(native_child_staffing, "_nonce", lambda: "nonce-rule4-one")
    return native_child_staffing.staff_native_child(
        store,
        host="claude",
        task=TASK,
        parent_session_id=SESSION,
        parent_trace_id=TRACE,
        launch_id="tool-use-rule4",
        binding_kind="launch_id",
        binding_id="tool-use-rule4",
        install_identity=_install(),
        install_identity_reader=lambda _host: _install(),
        config=AgencyConfig(ollama=OllamaConfig(enabled=False)),
        platform="windows",
        available_tools=AVAILABLE_TOOLS,
    )


def _bind_host_launch(store: Store) -> None:
    store.record_native_child_started(
        host="claude",
        backend="delegate_task",
        session_id=SESSION,
        trace_id=TRACE,
        worker_id=CHILD,
        native_run_id=f"claude-agent:{CHILD}",
    )
    assert (
        store.bind_native_child_launch(
            host="claude",
            session_id=SESSION,
            trace_id=TRACE,
            worker_id=CHILD,
            native_run_id=f"claude-agent:{CHILD}",
            launch_id="tool-use-rule4",
        )
        is True
    )


def _host_artifact(path: Path, launch_text: str) -> str:
    record = {
        "type": "user",
        "isSidechain": True,
        "agentId": CHILD,
        "sessionId": SESSION,
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "message": {"role": "user", "content": [{"type": "text", "text": launch_text}]},
    }
    payload = (json.dumps(record, separators=(",", ":")) + "\n").encode()
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def test_real_roster_multi_card_decision_reaches_launch_intact_without_load_authority(
    monkeypatch: pytest.MonkeyPatch,
    store: Store,
) -> None:
    result = _staff(monkeypatch, store)

    assert result.staffed is True
    assert result.selected_ids == SELECTED
    parsed = parse_inference_team_delivery(result.rewritten_task)
    assert parsed is not None
    assert parsed.original_task == TASK
    assert tuple(card.specialist_slug for card in parsed.cards) == SELECTED
    for card in parsed.cards:
        prompt = store.get_versioned_specialist_prompt(
            card.specialist_slug,
            card.specialist_version,
            card.specialist_prompt_hash,
        )
        assert prompt is not None
        assert prompt["prompt_body"] == card.prompt_body
    persisted = store.get_native_child_staffing_decision(result.decision_id)
    assert persisted is not None
    assert [card["specialist_slug"] for card in persisted["cards"]] == list(SELECTED)
    assert store.get_specialist_load_history(SESSION) == []
    assert store.get_delegations(TRACE) == []


def test_store_route_alone_is_diagnostic_but_host_artifact_verifies_once(
    monkeypatch: pytest.MonkeyPatch,
    store: Store,
    collector_lease,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence.storage_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    result = _staff(monkeypatch, store)
    collection = _begin_private_host_artifact_collection(collector_lease, host="claude")
    invocation_start = _start_private_host_invocation(collection)
    artifact = collection.root / "project" / SESSION / "subagents" / f"agent-{CHILD}.jsonl"
    artifact.parent.mkdir(parents=True)
    _host_artifact(artifact, result.rewritten_task)
    invocation = _finish_private_host_invocation(invocation_start)
    _bind_host_launch(store)

    diagnostic = child_delivery_evidence(artifact, host="claude")
    assert diagnostic is not None
    assert diagnostic.v6_delivery is True
    assert diagnostic.verified_delivery is False
    assert diagnostic.staffed is False

    capability = _collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=store,
    )
    assert capability is not None
    verified = capability.evidence
    assert verified is not None
    assert verified.verified_delivery is True
    assert verified.staffed is True
    assert tuple(card.specialist_slug for card in verified.cards) == SELECTED
    proof = _consume_verified_host_child_delivery(capability)
    assert proof is not None
    assert proof["decision_id"] == result.decision_id

    assert _consume_verified_host_child_delivery(capability) is None


def test_terminal_parent_cannot_create_a_new_staffing_decision(
    monkeypatch: pytest.MonkeyPatch,
    store: Store,
) -> None:
    assert store.close_turn_evidence(SESSION, TRACE, status="preflight_failed") == 1

    result = _staff(monkeypatch, store)

    assert result.staffed is False
    assert result.reason_code == "native_child_parent_scope_invalid"
    assert result.context_segment == ""
    assert result.decision_id == ""
