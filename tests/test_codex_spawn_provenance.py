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
_CHILD_THREAD = "019ff956-4849-7453-9174-8c5143ff5d29"
_DEPTH_TWO_PARENT = "019ff927-9be7-7073-88bc-e5857ce841f4"
_GRANDCHILD_THREAD = "019ff928-4178-7421-86f6-d391c6316d98"
_EXEC_SESSION = "019ff1e8-e0fe-7fe0-b8ba-57de219228c6"
_EXEC_CHILD = "019ff1e9-defe-77c2-8bd1-9d503f1670b6"
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


def _root_metadata(
    *,
    session_id: str = _SESSION,
    cli_version: str = "0.147.0",
    source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> dict[str, Any]:
    return _record(
        "session_meta",
        {
            "id": session_id,
            "session_id": session_id,
            "cli_version": cli_version,
            "history_mode": history_mode,
            "source": source,
            "thread_source": "user",
            "originator": originator,
        },
    )


def _subagent_metadata(
    *,
    thread_id: str,
    parent_thread_id: str,
    depth: int,
    cli_version: str = "0.147.0",
    root_session_id: str = _SESSION,
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> dict[str, Any]:
    return _record(
        "session_meta",
        {
            "id": thread_id,
            "session_id": root_session_id,
            "forked_from_id": parent_thread_id,
            "parent_thread_id": parent_thread_id,
            "cli_version": cli_version,
            "history_mode": history_mode,
            "originator": originator,
            "subagent_history_start_ordinal": None if history_mode == "legacy" else 27,
            "multi_agent_version": "v2",
            "agent_path": "/root/security_review",
            "agent_nickname": "Goodall",
            "source": {
                "subagent": {
                    "thread_spawn": {
                        "parent_thread_id": parent_thread_id,
                        "depth": depth,
                        "agent_path": "/root/security_review",
                        "agent_nickname": "Goodall",
                        "agent_role": None,
                    }
                }
            },
            "thread_source": "subagent",
        },
    )


def _records(
    *,
    args: dict[str, Any] | None = None,
    marker: object = _MISSING,
    cli_version: str = "0.147.0",
    call_id: str = _CALL,
    turn_id: str = _TURN,
    session_id: str = _SESSION,
    source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
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
        _root_metadata(
            session_id=session_id,
            cli_version=cli_version,
            source=source,
            history_mode=history_mode,
            originator=originator,
        ),
        _record("event_msg", {"type": "task_started", "turn_id": _TURN}),
        _record("response_item", call),
    ]


def _forked_records(
    *,
    thread_id: str = _CHILD_THREAD,
    parent_thread_id: str = _SESSION,
    depth: int = 1,
    parent_metadata: dict[str, Any] | None = None,
    marker: object = _MISSING,
    root_session_id: str = _SESSION,
    root_source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> list[dict[str, Any]]:
    records = _records(
        marker=marker,
        session_id=root_session_id,
        source=root_source,
        history_mode=history_mode,
        originator=originator,
    )
    return [
        _subagent_metadata(
            thread_id=thread_id,
            parent_thread_id=parent_thread_id,
            depth=depth,
            root_session_id=root_session_id,
            history_mode=history_mode,
            originator=originator,
        ),
        parent_metadata
        or _root_metadata(
            session_id=root_session_id,
            source=root_source,
            history_mode=history_mode,
            originator=originator,
        ),
        *records[1:],
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


@pytest.fixture
def forked_rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home
        / "sessions"
        / "2026"
        / "08"
        / "13"
        / f"rollout-2026-08-13T00-16-49-{_CHILD_THREAD}.jsonl"
    )
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    return path, {"CODEX_HOME": str(home)}


@pytest.fixture
def exec_rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home
        / "sessions"
        / "2026"
        / "08"
        / "11"
        / f"rollout-2026-08-11T13-41-04-{_EXEC_CHILD}.jsonl"
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
    session_id: str = _SESSION,
) -> subject.CodexPlaintextSpawnAttestation | None:
    return subject.attest_codex_plaintext_spawn(
        path,
        session_id=session_id,
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


def test_exact_forked_child_shape_attests_and_binds_thread_and_root(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _CHILD_THREAD
    assert attestation.root_session_id == _SESSION
    assert attestation.ancestry_thread_ids == (_CHILD_THREAD, _SESSION)
    assert len(attestation.ancestry_lengths) == 2
    assert all(length > 0 for length in attestation.ancestry_lengths)
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_exact_exec_root_shape_attests(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = exec_rollout
    path = original.with_name(f"rollout-2026-08-11T13-39-59-{_EXEC_SESSION}.jsonl")
    _write(
        path,
        _records(
            marker=[],
            session_id=_EXEC_SESSION,
            source="exec",
            history_mode="legacy",
            originator="codex_exec",
        ),
    )

    attestation = _attest(path, environ, session_id=_EXEC_SESSION)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _EXEC_SESSION
    assert attestation.root_session_id == _EXEC_SESSION
    assert attestation.ancestry_thread_ids == (_EXEC_SESSION,)


def test_exact_exec_depth_one_child_shape_attests(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = exec_rollout
    _write(
        path,
        _forked_records(
            thread_id=_EXEC_CHILD,
            parent_thread_id=_EXEC_SESSION,
            root_session_id=_EXEC_SESSION,
            root_source="exec",
            history_mode="legacy",
            originator="codex_exec",
            marker=[],
        ),
    )

    attestation = _attest(path, environ, session_id=_EXEC_SESSION)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _EXEC_CHILD
    assert attestation.root_session_id == _EXEC_SESSION
    assert attestation.ancestry_thread_ids == (_EXEC_CHILD, _EXEC_SESSION)


@pytest.mark.parametrize(
    ("source", "history_mode", "originator"),
    [
        ("cli", "legacy", "codex-tui"),
        ("exec", "paginated", "codex_exec"),
        ("unknown", "legacy", "codex_exec"),
        ("exec", "unknown", "codex_exec"),
        ("exec", "legacy", "codex-tui"),
        ("cli", "paginated", "codex_exec"),
    ],
)
def test_root_rollout_rejects_cross_mixed_or_unknown_lineage(
    rollout: tuple[Path, dict[str, str]],
    source: str,
    history_mode: str,
    originator: str,
) -> None:
    path, environ = rollout
    _write(
        path,
        _records(
            marker=[],
            source=source,
            history_mode=history_mode,
            originator=originator,
        ),
    )

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "child_history",
        "child_originator",
        "root_source",
        "root_history",
        "missing_child_history",
        "missing_root_source",
        "exec_history_start",
    ],
)
def test_exec_child_and_root_must_share_one_exact_lineage(
    exec_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    path, environ = exec_rollout
    records = _forked_records(
        thread_id=_EXEC_CHILD,
        parent_thread_id=_EXEC_SESSION,
        root_session_id=_EXEC_SESSION,
        root_source="exec",
        history_mode="legacy",
        originator="codex_exec",
        marker=[],
    )
    child = records[0]["payload"]
    root = records[1]["payload"]
    if mutation == "child_history":
        child["history_mode"] = "paginated"
    elif mutation == "child_originator":
        child["originator"] = "codex-tui"
    elif mutation == "root_source":
        root["source"] = "cli"
    elif mutation == "root_history":
        root["history_mode"] = "paginated"
    elif mutation == "missing_child_history":
        child.pop("history_mode")
    elif mutation == "missing_root_source":
        root.pop("source")
    elif mutation == "exec_history_start":
        child["subagent_history_start_ordinal"] = 27
    _write(path, records)

    assert _attest(path, environ, session_id=_EXEC_SESSION) is None


def test_unobserved_exec_depth_two_shape_fails_closed(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = exec_rollout
    current = "019ff1ea-0000-7000-8000-000000000001"
    path = original.with_name(f"rollout-2026-08-11T13-42-00-{current}.jsonl")
    parent = _subagent_metadata(
        thread_id=_EXEC_CHILD,
        parent_thread_id=_EXEC_SESSION,
        depth=1,
        root_session_id=_EXEC_SESSION,
        history_mode="legacy",
        originator="codex_exec",
    )
    _write(
        path,
        _forked_records(
            thread_id=current,
            parent_thread_id=_EXEC_CHILD,
            depth=2,
            parent_metadata=parent,
            root_session_id=_EXEC_SESSION,
            root_source="exec",
            history_mode="legacy",
            originator="codex_exec",
            marker=[],
        ),
    )

    assert _attest(path, environ, session_id=_EXEC_SESSION) is None


def test_exact_depth_two_forked_child_shape_attests(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = forked_rollout
    path = original.with_name(f"rollout-2026-08-13T00-16-49-{_GRANDCHILD_THREAD}.jsonl")
    parent = _subagent_metadata(
        thread_id=_DEPTH_TWO_PARENT,
        parent_thread_id=_SESSION,
        depth=1,
    )
    _write(
        path,
        _forked_records(
            thread_id=_GRANDCHILD_THREAD,
            parent_thread_id=_DEPTH_TWO_PARENT,
            depth=2,
            parent_metadata=parent,
            marker=[],
        ),
    )

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _GRANDCHILD_THREAD
    assert attestation.ancestry_thread_ids == (
        _GRANDCHILD_THREAD,
        _DEPTH_TWO_PARENT,
    )
    assert attestation.root_session_id == _SESSION


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_parent",
        "reordered",
        "duplicate_thread",
        "current_depth_three",
        "parent_depth_two",
        "parent_root_link",
        "explicit_root_third_meta",
    ],
)
def test_depth_two_fork_requires_exact_observed_two_record_chain(
    forked_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    original, environ = forked_rollout
    path = original.with_name(f"rollout-2026-08-13T00-16-49-{_GRANDCHILD_THREAD}.jsonl")
    parent = _subagent_metadata(
        thread_id=_DEPTH_TWO_PARENT,
        parent_thread_id=_SESSION,
        depth=1,
    )
    records = _forked_records(
        thread_id=_GRANDCHILD_THREAD,
        parent_thread_id=_DEPTH_TWO_PARENT,
        depth=2,
        parent_metadata=parent,
        marker=[],
    )
    if mutation == "missing_parent":
        records.pop(1)
    elif mutation == "reordered":
        records[:2] = reversed(records[:2])
    elif mutation == "duplicate_thread":
        records[1]["payload"]["id"] = _GRANDCHILD_THREAD
    elif mutation == "current_depth_three":
        records[0]["payload"]["source"]["subagent"]["thread_spawn"]["depth"] = 3
    elif mutation == "parent_depth_two":
        records[1]["payload"]["source"]["subagent"]["thread_spawn"]["depth"] = 2
    elif mutation == "parent_root_link":
        records[1]["payload"]["forked_from_id"] = _CHILD_THREAD
    elif mutation == "explicit_root_third_meta":
        records.insert(2, _root_metadata())
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "thread_id",
        "root_session_id",
        "parent_thread_id",
        "forked_from_id",
        "source_parent_thread_id",
        "depth",
        "parent_id",
        "extra_source_key",
        "history_start_type",
        "history_start_null",
        "multi_agent_version",
        "top_level_agent_path",
        "third_session_meta",
        "nonleading_parent_meta",
    ],
)
def test_forked_rollout_requires_exact_thread_root_and_parent_ancestry(
    forked_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    path, environ = forked_rollout
    records = _forked_records(marker=[])
    child = records[0]["payload"]
    parent = records[1]["payload"]
    unrelated = "019ff999-9999-7999-8999-999999999999"
    if mutation == "thread_id":
        child["id"] = unrelated
    elif mutation == "root_session_id":
        child["session_id"] = _CHILD_THREAD
    elif mutation == "parent_thread_id":
        child["parent_thread_id"] = unrelated
    elif mutation == "forked_from_id":
        child["forked_from_id"] = unrelated
    elif mutation == "source_parent_thread_id":
        child["source"]["subagent"]["thread_spawn"]["parent_thread_id"] = unrelated
    elif mutation == "depth":
        child["source"]["subagent"]["thread_spawn"]["depth"] = 2
    elif mutation == "parent_id":
        parent["id"] = unrelated
    elif mutation == "extra_source_key":
        child["source"]["forged"] = {}
    elif mutation == "history_start_type":
        child["subagent_history_start_ordinal"] = True
    elif mutation == "history_start_null":
        child["subagent_history_start_ordinal"] = None
    elif mutation == "multi_agent_version":
        child["multi_agent_version"] = "v1"
    elif mutation == "top_level_agent_path":
        child["agent_path"] = "/root/different"
    elif mutation == "third_session_meta":
        records.insert(2, _root_metadata())
    elif mutation == "nonleading_parent_meta":
        records[1:3] = [records[2], records[1]]
    _write(path, records)

    assert _attest(path, environ) is None


def test_forked_rollout_rejects_thread_identity_as_root_session_identity(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=_CHILD_THREAD,
            turn_id=_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "tui"),
        ("thread_source", "subagent"),
        ("forked_from_id", _CHILD_THREAD),
        ("parent_thread_id", _CHILD_THREAD),
    ],
)
def test_root_rollout_requires_exact_nonforked_metadata(
    rollout: tuple[Path, dict[str, str]], field: str, value: object
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    records[0]["payload"][field] = value
    _write(path, records)

    assert _attest(path, environ) is None


def test_forked_parent_record_mutation_invalidates_attestation(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    raw = path.read_bytes()
    assert raw.count(b'"source":"cli"') == 1
    path.write_bytes(raw.replace(b'"source":"cli"', b'"source":"tui"'))

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )


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
