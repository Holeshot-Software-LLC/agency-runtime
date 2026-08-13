"""Adversarial tests for Codex plaintext spawn transcript provenance."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import codex_spawn_provenance as subject

_SESSION = "019ff8ee-eb1c-7de3-815d-3deea9eca028"
_TURN = "019ff8ef-c6e1-7961-a682-d8aa9f11f464"
_CALL = "call_4fLyxjPXggCL0L9VWsSXDWr3"
_ARGS = {
    "task_name": "security_review",
    "message": "Review the exact transaction boundary.",
    "fork_turns": "all",
}
_MISSING = object()


def _record(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"timestamp": "2026-08-13T00:00:00Z", "type": kind, "payload": payload}


def _records(
    *,
    args: dict[str, Any] | None = None,
    marker: object = _MISSING,
    cli_version: str = "0.147.0",
    call_id: str = _CALL,
    turn_id: str = _TURN,
) -> list[dict[str, Any]]:
    call = {
        "type": "function_call",
        "namespace": "collaboration",
        "name": "spawn_agent",
        "arguments": json.dumps(args or _ARGS, separators=(",", ":")),
        "call_id": call_id,
        "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
    }
    if marker is not _MISSING:
        call["encrypted_function_args"] = marker
    return [
        _record(
            "session_meta",
            {
                "id": _SESSION,
                "session_id": _SESSION,
                "cli_version": cli_version,
            },
        ),
        _record("event_msg", {"type": "task_started", "turn_id": _TURN}),
        _record("response_item", call),
    ]


@pytest.fixture
def rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home / "sessions" / "2026" / "08" / "12" / f"rollout-2026-08-12T22-23-55-{_SESSION}.jsonl"
    )
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    return path, {"CODEX_HOME": str(home)}


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )


def _attest(
    path: Path,
    environ: dict[str, str],
    *,
    tool_input: object = _ARGS,
) -> subject.CodexPlaintextSpawnAttestation | None:
    return subject.attest_codex_plaintext_spawn(
        path,
        session_id=_SESSION,
        turn_id=_TURN,
        tool_use_id=_CALL,
        tool_input=tool_input,
        environ=environ,
    )


def test_exact_marked_spawn_attests_and_tolerates_unrelated_append(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.cli_version == "0.147.0"
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_record("event_msg", {"type": "token_count"})) + "\n")
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


@pytest.mark.parametrize("marker", [_MISSING, None, ["ciphertext"], {}, "[]"])
def test_missing_null_or_nonempty_marker_never_attests(
    rollout: tuple[Path, dict[str, str]], marker: object
) -> None:
    path, environ = rollout
    _write(path, _records(marker=marker))

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"cli_version": "0.147.0-alpha.6.6"},
        {"call_id": "different-call"},
        {"turn_id": "different-turn"},
    ],
)
def test_version_or_correlation_drift_never_attests(
    rollout: tuple[Path, dict[str, str]], mutation: dict[str, str]
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], **mutation))

    assert _attest(path, environ) is None


def test_full_arguments_and_pinned_schema_must_match(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    transcript_args = {**_ARGS, "message": "different"}
    _write(path, _records(args=transcript_args, marker=[]))
    assert _attest(path, environ) is None

    unknown = {**_ARGS, "future_field": True}
    _write(path, _records(args=unknown, marker=[]))
    assert _attest(path, environ, tool_input=unknown) is None


def test_duplicate_json_keys_and_ambiguous_calls_fail(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    _write(path, records)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            '"encrypted_function_args":[]',
            '"encrypted_function_args":[],"encrypted_function_args":[]',
        ),
        encoding="utf-8",
    )
    assert _attest(path, environ) is None

    _write(path, [*records, records[-1]])
    assert _attest(path, environ) is None


@pytest.mark.parametrize("terminal", ["function_call_output", "task_complete"])
def test_completed_or_output_call_is_stale_before_attestation(
    rollout: tuple[Path, dict[str, str]], terminal: str
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    if terminal == "function_call_output":
        records.append(_record("response_item", {"type": terminal, "call_id": _CALL}))
    else:
        records.append(_record("event_msg", {"type": terminal, "turn_id": _TURN}))
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize("terminal", ["function_call", "function_call_output", "task_complete"])
def test_append_replay_output_or_completion_invalidates_attestation(
    rollout: tuple[Path, dict[str, str]], terminal: str
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    _write(path, records)
    attestation = _attest(path, environ)
    assert attestation is not None
    appended = (
        records[-1]
        if terminal == "function_call"
        else _record(
            "response_item" if terminal == "function_call_output" else "event_msg",
            (
                {"type": terminal, "call_id": _CALL}
                if terminal == "function_call_output"
                else {"type": terminal, "turn_id": _TURN}
            ),
        )
    )
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(appended, separators=(",", ":")) + "\n")

    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_record_mutation_and_forged_seal_are_rejected(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    raw = path.read_bytes()
    original = b"Review the exact transaction boundary."
    replacement = b"Review the exact transaction boundary!"
    assert len(original) == len(replacement)
    path.write_bytes(raw.replace(original, replacement))
    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        replace(attestation, call_sha256="0" * 64), tool_input=_ARGS
    )


def test_path_escape_relative_path_hardlink_and_incomplete_record_fail(
    rollout: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    assert (
        subject.attest_codex_plaintext_spawn(
            Path(path.name),
            session_id=_SESSION,
            turn_id=_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )
    escaped = tmp_path / path.name
    escaped.write_bytes(path.read_bytes())
    assert _attest(escaped, environ) is None

    link = path.with_name("linked.jsonl")
    try:
        os.link(path, link)
    except OSError:
        pytest.skip("hard links are unavailable")
    try:
        assert _attest(path, environ) is None
    finally:
        link.unlink()
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    assert _attest(path, environ) is None


def test_observed_large_rollout_line_is_supported_but_argument_budget_is_bounded(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    large = {**_ARGS, "message": "x" * (600 * 1024)}
    _write(path, _records(args=large, marker=[]))
    attestation = _attest(path, environ, tool_input=large)
    assert attestation is not None
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=large)

    oversized = {**_ARGS, "message": "x" * (1024 * 1024)}
    _write(path, _records(args=oversized, marker=[]))
    assert _attest(path, environ, tool_input=oversized) is None
