"""Focused hook integration tests for authenticated Codex plaintext spawns."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core import (
    codex_spawn_provenance,
    native_child_install_identity,
    native_child_staffing,
)
from agency_runtime.core.native_child_staffing import NativeChildStaffingResult

_TASK = "Review the transaction boundary and add regression tests."
_SESSION_ID = "019ff8ee-eb1c-7de3-815d-3deea9eca028"
_TURN_ID = "019ff8ef-c6e1-7961-a682-d8aa9f11f464"
_CALL_ID = "call_4fLyxjPXggCL0L9VWsSXDWr3"
_FUNCTION_ITEM_ID = "fc_" + "a" * 50
_ARGS = {
    "message": _TASK,
    "task_name": "transaction_review",
    "fork_turns": "all",
}


class _LiveParentStore:
    def get_run(self, trace_id: str) -> dict[str, str] | None:
        if trace_id != _TURN_ID:
            return None
        return {
            "trace_id": trace_id,
            "session_id": _SESSION_ID,
            "host": "codex",
            "status": "active",
        }


def _payload(
    *,
    message: str = _TASK,
    tool_name: str = "functions.collaboration.spawn_agent",
    transcript_path: str = "C:\\codex-home\\sessions\\rollout-parent-session.jsonl",
) -> dict[str, Any]:
    args = {**_ARGS, "message": message}
    return {
        "hook_event_name": "PreToolUse",
        "session_id": _SESSION_ID,
        "turn_id": _TURN_ID,
        "tool_use_id": _CALL_ID,
        "tool_name": tool_name,
        "transcript_path": transcript_path,
        "tool_input": args,
    }


def _bridge() -> HookBridge:
    return HookBridge(
        "codex",
        store=_LiveParentStore(),  # type: ignore[arg-type]
        _master={"enabled": True},
    )


def _staffed(rewritten_task: str) -> NativeChildStaffingResult:
    return NativeChildStaffingResult(
        staffed=True,
        reason_code="staffed",
        rewritten_task=rewritten_task,
        context_segment="\n\n[authenticated team]",
        decision_id="decision-one",
        selected_ids=("reviewer",),
    )


def _unstaffed() -> NativeChildStaffingResult:
    return NativeChildStaffingResult(
        staffed=False,
        reason_code="native_child_delivery_validation_failed",
        rewritten_task=_TASK,
    )


def _install_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        native_child_install_identity,
        "current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )


def test_real_attestor_and_hook_integration_rewrites_exact_marked_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "codex-home"
    transcript = (
        home
        / "sessions"
        / "2026"
        / "08"
        / "12"
        / f"rollout-2026-08-12T22-23-55-{_SESSION_ID}.jsonl"
    )
    transcript.parent.mkdir(parents=True)
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": _SESSION_ID,
                "session_id": _SESSION_ID,
                "cli_version": "0.147.0",
                "source": "cli",
                "thread_source": "user",
                "history_mode": "paginated",
                "originator": "codex-tui",
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": _TURN_ID},
        },
        {
            "timestamp": "2026-08-12T22:23:55.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": _CALL_ID,
                "id": _FUNCTION_ITEM_ID,
                "arguments": json.dumps(_ARGS, separators=(",", ":")),
                "internal_chat_message_metadata_passthrough": {"turn_id": _TURN_ID},
                "encrypted_function_args": [],
            },
        },
    ]
    transcript.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setattr(
        codex_spawn_provenance,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        codex_spawn_provenance,
        "storage_file_is_trusted",
        lambda *_args, **_kwargs: True,
    )

    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        rewritten = kwargs["task"] + "\n\n[authenticated team]"
        assert kwargs["delivery_validator"](rewritten) is True
        assert kwargs["final_delivery_validator"]() is True
        return _staffed(rewritten)

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    _install_stub(monkeypatch)

    result = _bridge().handle(_payload(transcript_path=str(transcript)))

    assert result["hookSpecificOutput"]["updatedInput"]["message"].endswith("[authenticated team]")


@pytest.mark.parametrize(
    "tool_name",
    [
        "Agent",
        "spawn_agent",
        "collaborationspawn_agent",
        "functions.collaboration.spawn_agent",
    ],
)
def test_authenticated_codex_spawn_alias_routes_through_plaintext_staffing(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
) -> None:
    attestation = object()
    attest_calls: list[dict[str, Any]] = []
    current_calls: list[tuple[object, object]] = []
    staffing_calls: list[dict[str, Any]] = []

    def attest(transcript_path: object, **kwargs: Any) -> object:
        attest_calls.append({"transcript_path": transcript_path, **kwargs})
        return attestation

    def is_current(actual: object, *, tool_input: object) -> bool:
        current_calls.append((actual, tool_input))
        return True

    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        staffing_calls.append(kwargs)
        rewritten = kwargs["task"] + "\n\n[authenticated team]"
        assert kwargs["delivery_validator"](rewritten) is True
        assert kwargs["final_delivery_validator"]() is True
        return _staffed(rewritten)

    monkeypatch.setattr(codex_spawn_provenance, "attest_codex_plaintext_spawn", attest)
    monkeypatch.setattr(
        codex_spawn_provenance,
        "codex_plaintext_spawn_attestation_is_current",
        is_current,
    )
    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    _install_stub(monkeypatch)

    result = _bridge().handle(_payload(tool_name=tool_name))

    assert result["hookSpecificOutput"]["updatedInput"] == {
        **_ARGS,
        "message": _TASK + "\n\n[authenticated team]",
    }
    assert attest_calls == [
        {
            "transcript_path": "C:\\codex-home\\sessions\\rollout-parent-session.jsonl",
            "session_id": _SESSION_ID,
            "turn_id": _TURN_ID,
            "tool_use_id": _CALL_ID,
            "tool_input": _ARGS,
            "environ": os.environ,
        }
    ]
    assert len(staffing_calls) == 1
    assert staffing_calls[0]["host"] == "codex"
    assert staffing_calls[0]["task"] == _TASK
    assert staffing_calls[0]["launch_id"] == _CALL_ID
    assert current_calls == [(attestation, _ARGS), (attestation, _ARGS)]


@pytest.mark.parametrize("message", ["gAAAAA" + "x" * 80, "plaintext-looking task"])
def test_unattested_codex_spawn_stays_unstaffed_with_existing_reason(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    failures: list[dict[str, Any]] = []

    monkeypatch.setattr(
        codex_spawn_provenance,
        "attest_codex_plaintext_spawn",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        native_child_staffing,
        "staff_native_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unattested Codex input reached staffing")
        ),
    )
    monkeypatch.setattr(
        native_child_staffing,
        "record_native_child_staffing_failure",
        lambda _store, **kwargs: failures.append(kwargs) or "diagnostic-one",
    )

    assert _bridge().handle(_payload(message=message)) == {}
    assert len(failures) == 1
    assert failures[0]["reason_code"] == "unsupported_opaque_interagent_channel"
    assert failures[0]["launch_id"] == _CALL_ID
    assert failures[0]["task"] == message


def test_shared_plaintext_helper_refuses_codex_without_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        native_child_staffing,
        "staff_native_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Codex bypass reached staffing")
        ),
    )

    payload = _payload()
    assert (
        _bridge()._staff_plaintext_native_child(
            payload=payload,
            args=payload["tool_input"],
            task_field="message",
            task=_TASK,
        )
        == {}
    )


def _freshness_sequence(values: list[bool]) -> Iterator[bool]:
    yield from values


def test_attestation_drift_inside_delivery_validator_suppresses_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation = object()
    freshness = _freshness_sequence([False])

    monkeypatch.setattr(
        codex_spawn_provenance,
        "attest_codex_plaintext_spawn",
        lambda *_args, **_kwargs: attestation,
    )
    monkeypatch.setattr(
        codex_spawn_provenance,
        "codex_plaintext_spawn_attestation_is_current",
        lambda actual, *, tool_input: actual is attestation and next(freshness),
    )

    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        rewritten = kwargs["task"] + "\n\n[must not escape]"
        assert kwargs["delivery_validator"](rewritten) is False
        return _unstaffed()

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    _install_stub(monkeypatch)

    assert _bridge().handle(_payload()) == {}


def test_attestation_drift_during_final_transaction_validation_suppresses_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation = object()
    freshness = _freshness_sequence([True, False])

    monkeypatch.setattr(
        codex_spawn_provenance,
        "attest_codex_plaintext_spawn",
        lambda *_args, **_kwargs: attestation,
    )
    monkeypatch.setattr(
        codex_spawn_provenance,
        "codex_plaintext_spawn_attestation_is_current",
        lambda actual, *, tool_input: actual is attestation and next(freshness),
    )

    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        rewritten = kwargs["task"] + "\n\n[must not escape]"
        assert kwargs["delivery_validator"](rewritten) is True
        assert kwargs["final_delivery_validator"]() is False
        return _unstaffed()

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    _install_stub(monkeypatch)

    assert _bridge().handle(_payload()) == {}
