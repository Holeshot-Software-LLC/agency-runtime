"""Rule 4, independently verified: read the host's own artifact for the card.

These tests exist because ``specialists_loaded`` is written by the code under
test. Everything here reads a transcript the *host* wrote and asks whether the
card actually arrived — and, just as importantly, refuses to count a marker the
child merely read back later.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.cli import evidence_commands
from agency_runtime.cli.evidence_commands import cmd_evidence_children
from agency_runtime.core import child_delivery_evidence as subject
from agency_runtime.core.child_delivery_evidence import (
    MAX_LAUNCH_PREFIX_BYTES,
    _begin_private_host_artifact_collection,
    _collect_private_host_child_delivery,
    _consume_verified_host_child_delivery,
    _ExpectedChildDelivery,
    _finish_private_host_invocation,
    _start_private_host_invocation,
    _verify_child_delivery_evidence,
    child_delivery_evidence,
    child_delivery_projection,
    claude_child_delivery_evidence,
    codex_child_delivery_evidence,
    codex_v1491_child_parent_session,
    scan_child_delivery_evidence,
)
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.native_child_prompt_delivery import (
    InferenceTeamCard,
    inference_team_digest,
    render_inference_team_delivery,
    render_jit_specialist_delivery,
)
from agency_runtime.core.private_paths import _private_temporary_directory_lease
from agency_runtime.core.roster.revisions import content_digest

PARENT_SESSION = "37a4776a-92f4-4fe8-b2fe-926652d70225"
CHILD_AGENT = "a19cc709eae42e6aa"
CODEX_CHILD_SESSION = "019fbb8b-1394-7413-a7bd-366714f530ad"
CODEX_V1491_PARENT_SESSION = "01a041aa-830d-7a33-915b-fb8e8bf8e0f3"
CODEX_V1491_CHILD_SESSION = "01a041ac-427c-7333-8616-12672552ce9b"
CODEX_V1491_WINDOW_ID = "01a041ac-427c-7333-8616-12740adee42c"
PROMPT = "You are a SQLite specialist. Prefer WAL mode and bounded transactions."
OTHER_PROMPT = "You are a security reviewer. Name the exact attacker capability."
_NOW = datetime.now(timezone.utc).replace(microsecond=0)
ISSUED_AT = _NOW.isoformat(timespec="seconds").replace("+00:00", "Z")
OBSERVED_AT = (_NOW + timedelta(seconds=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
EXPIRES_AT = (_NOW + timedelta(minutes=5)).isoformat(timespec="seconds").replace("+00:00", "Z")
RUNTIME_DIGEST = content_digest("runtime")


@pytest.fixture
def private_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat the fixture root as ACL-private, the way a real host directory is.

    Windows ``Temp`` is not private, so a synthetic artifact can never satisfy
    the real gate. ``test_a_directory_other_accounts_can_write_is_refused``
    leaves the gate alone and proves it still bites.
    """

    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)


@pytest.fixture
def collector_lease():
    """Keep one allocator-owned opaque lease alive for collector tests."""

    with _private_temporary_directory_lease(prefix="child-proof-test") as lease:
        yield lease


@pytest.fixture
def canonical_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = subject.default_child_artifact_root

    def root(host: str) -> Path:
        normalized = str(host).strip().casefold()
        if normalized in {"claude", "codex"}:
            return tmp_path
        return original(host)

    monkeypatch.setattr(subject, "default_child_artifact_root", root)


def _envelope(
    task: str,
    prompt: str = PROMPT,
    *,
    host: str = "claude",
    slug: str = "database-engineer",
    parent_session_id: str = PARENT_SESSION,
) -> str:
    return render_jit_specialist_delivery(
        task,
        prompt,
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id="trace-9f2c",
        tool_use_id="toolu_01ABC",
        specialist_slug=slug,
        specialist_version=content_digest(prompt),
        specialist_prompt_hash=content_digest(prompt),
    )


def _claude_record(
    text: object,
    *,
    record_type: str = "user",
    sidechain: bool = True,
    timestamp: str = OBSERVED_AT,
) -> dict[str, object]:
    return {
        "parentUuid": None,
        "isSidechain": sidechain,
        "agentId": CHILD_AGENT,
        "type": record_type,
        "message": {"role": "user", "content": text},
        "sessionId": PARENT_SESSION,
        "timestamp": timestamp,
    }


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _claude_artifact(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    return _write_jsonl(
        tmp_path / "proj" / PARENT_SESSION / "subagents" / f"agent-{CHILD_AGENT}.jsonl",
        records,
    )


def _codex_meta(*, spawned: bool) -> dict[str, object]:
    payload: dict[str, object] = {"id": CODEX_CHILD_SESSION}
    if spawned:
        payload["source"] = {
            "subagent": {"thread_spawn": {"parent_thread_id": PARENT_SESSION, "depth": 1}}
        }
    return {"timestamp": "2026-08-01T04:18:04.132Z", "type": "session_meta", "payload": payload}


def _codex_message(text: str, *, role: str = "developer") -> dict[str, object]:
    return {
        "timestamp": "2026-08-01T04:18:05.000Z",
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "content": [{"type": "input_text", "text": text}],
        },
    }


def _codex_artifact(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    return _write_jsonl(
        tmp_path
        / "2026"
        / "08"
        / "01"
        / f"rollout-2026-08-01T00-18-01-{CODEX_CHILD_SESSION}.jsonl",
        records,
    )


def _codex_v1491_meta(*, cwd: Path) -> dict[str, object]:
    return {
        "timestamp": "2026-08-27T05:23:23.457Z",
        "type": "session_meta",
        "payload": {
            "id": CODEX_V1491_CHILD_SESSION,
            "timestamp": "2026-08-27T05:23:23.389Z",
            "session_id": CODEX_V1491_PARENT_SESSION,
            "parent_thread_id": CODEX_V1491_PARENT_SESSION,
            "source": {
                "subagent": {
                    "thread_spawn": {
                        "parent_thread_id": CODEX_V1491_PARENT_SESSION,
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
            "context_window": {"window_id": CODEX_V1491_WINDOW_ID},
            "history_mode": "paginated",
            "thread_source": "subagent",
            "multi_agent_version": "v2",
        },
        "ordinal": 0,
    }


def _codex_v1501_meta(*, cwd: Path) -> dict[str, object]:
    meta = copy.deepcopy(_codex_v1491_meta(cwd=cwd))
    payload = meta["payload"]
    assert isinstance(payload, dict)
    payload["cli_version"] = "0.150.1"
    payload["agent_role"] = "Code Reviewer"
    source = payload["source"]
    assert isinstance(source, dict)
    subagent = source["subagent"]
    assert isinstance(subagent, dict)
    spawn = subagent["thread_spawn"]
    assert isinstance(spawn, dict)
    spawn["agent_role"] = "Code Reviewer"
    return meta


def _codex_v1491_artifact(
    root: Path,
    *,
    cwd: Path,
    meta: dict[str, object] | None = None,
) -> Path:
    return _write_jsonl(
        root
        / "2026"
        / "08"
        / "27"
        / f"rollout-2026-08-27T05-23-23-{CODEX_V1491_CHILD_SESSION}.jsonl",
        [meta or _codex_v1491_meta(cwd=cwd)],
    )


@pytest.fixture
def codex_v1491_artifact_trust(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model the owner-integrity probes while retaining real link checks."""

    monkeypatch.setattr(
        subject,
        "storage_artifact_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_args, **_kwargs: True)


def test_codex_v1491_child_metadata_resolves_the_exact_host_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_artifact(root, cwd=cwd)
    monkeypatch.setattr(subject, "default_child_artifact_root", lambda host: root)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
        )
        == CODEX_V1491_PARENT_SESSION
    )


def test_codex_v1501_child_metadata_resolves_the_exact_explicit_role_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_artifact(
        root,
        cwd=cwd,
        meta=_codex_v1501_meta(cwd=cwd),
    )
    monkeypatch.setattr(subject, "default_child_artifact_root", lambda host: root)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
        )
        == CODEX_V1491_PARENT_SESSION
    )


def _codex_forward_meta(*, cwd: Path, cli_version: str = "0.151.0") -> dict[str, object]:
    """Model a newer host release whose shape matches the 0.150.1 contract.

    Mirrors the retained real 0.151.0 child session metadata from the
    2026-08-29 live harness: identical keys and lineage nesting, only the
    ``cli_version`` differs (AR-334).
    """

    meta = copy.deepcopy(_codex_v1501_meta(cwd=cwd))
    payload = meta["payload"]
    assert isinstance(payload, dict)
    payload["cli_version"] = cli_version
    return meta


def test_codex_forward_release_child_metadata_resolves_under_newest_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_artifact(root, cwd=cwd, meta=_codex_forward_meta(cwd=cwd))
    monkeypatch.setattr(subject, "default_child_artifact_root", lambda host: root)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
        )
        == CODEX_V1491_PARENT_SESSION
    )


def test_codex_forward_release_tolerates_bounded_additive_metadata(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    meta = _codex_forward_meta(cwd=cwd, cli_version="0.152.3")
    payload = meta["payload"]
    assert isinstance(payload, dict)
    payload["internal_chat_message_metadata_passthrough"] = {}
    payload["collaboration_mode_kind"] = "default"
    artifact = _codex_v1491_artifact(root, cwd=cwd, meta=meta)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == CODEX_V1491_PARENT_SESSION
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "prerelease_version",
        "older_than_baseline",
        "unknown_key_flood",
        "missing_required_role",
        "forked_history_marker",
    ],
)
def test_codex_forward_release_contract_drift_fails_closed(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
    mutation: str,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    meta = _codex_forward_meta(cwd=cwd)
    payload = meta["payload"]
    assert isinstance(payload, dict)
    if mutation == "prerelease_version":
        payload["cli_version"] = "0.151.0-nightly"
    elif mutation == "older_than_baseline":
        payload["cli_version"] = "0.149.2"
    elif mutation == "unknown_key_flood":
        for index in range(9):
            payload[f"additive_key_{index}"] = index
    elif mutation == "missing_required_role":
        del payload["agent_role"]
    elif mutation == "forked_history_marker":
        payload["forked_from_id"] = CODEX_V1491_PARENT_SESSION
    else:  # pragma: no cover - the parameter list is closed above
        raise AssertionError(f"unhandled mutation: {mutation}")
    artifact = _codex_v1491_artifact(root, cwd=cwd, meta=meta)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


def test_codex_rollout_filename_accepts_utc_and_host_local_wall_time() -> None:
    payload_at = datetime(2026, 8, 27, 5, 23, 23, tzinfo=timezone.utc)
    utc_wall = payload_at.replace(tzinfo=None)
    local_wall = payload_at.astimezone().replace(tzinfo=None)

    assert subject._codex_rollout_wall_matches(utc_wall, payload_at)
    assert subject._codex_rollout_wall_matches(local_wall, payload_at)
    assert not subject._codex_rollout_wall_matches(
        utc_wall + timedelta(seconds=1),
        payload_at,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_top_level_role",
        "mismatched_top_level_role",
        "missing_nested_role",
        "mismatched_nested_role",
    ],
)
def test_codex_v1501_child_metadata_role_drift_fails_closed(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
    mutation: str,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    meta = _codex_v1501_meta(cwd=cwd)
    payload = meta["payload"]
    assert isinstance(payload, dict)
    source = payload["source"]
    assert isinstance(source, dict)
    subagent = source["subagent"]
    assert isinstance(subagent, dict)
    spawn = subagent["thread_spawn"]
    assert isinstance(spawn, dict)
    if mutation == "missing_top_level_role":
        del payload["agent_role"]
    elif mutation == "mismatched_top_level_role":
        payload["agent_role"] = "default"
    elif mutation == "missing_nested_role":
        del spawn["agent_role"]
    elif mutation == "mismatched_nested_role":
        spawn["agent_role"] = "default"
    else:  # pragma: no cover - the parameter list is closed above
        raise AssertionError(f"unhandled mutation: {mutation}")
    artifact = _codex_v1491_artifact(root, cwd=cwd, meta=meta)

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "child_mismatch",
        "parent_disagreement",
        "wrong_version",
        "nested_child",
        "assigned_role",
        "inherited_history",
        "wrong_originator",
        "wrong_history_mode",
        "wrong_cwd",
        "source_shape_drift",
        "agent_metadata_disagreement",
        "invalid_context_window",
        "noncausal_timestamp",
    ],
)
def test_codex_v1491_child_metadata_semantic_drift_fails_closed(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
    mutation: str,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    meta = copy.deepcopy(_codex_v1491_meta(cwd=cwd))
    payload = meta["payload"]
    assert isinstance(payload, dict)
    source = payload["source"]
    assert isinstance(source, dict)
    subagent = source["subagent"]
    assert isinstance(subagent, dict)
    spawn = subagent["thread_spawn"]
    assert isinstance(spawn, dict)

    if mutation == "child_mismatch":
        payload["id"] = CODEX_V1491_WINDOW_ID
    elif mutation == "parent_disagreement":
        payload["parent_thread_id"] = "01a041aa-830e-7a33-915b-fb8e8bf8e0f3"
    elif mutation == "wrong_version":
        payload["cli_version"] = "0.150.0"
    elif mutation == "nested_child":
        spawn["depth"] = 2
    elif mutation == "assigned_role":
        spawn["agent_role"] = "code-reviewer"
    elif mutation == "inherited_history":
        payload["forked_from_id"] = CODEX_V1491_PARENT_SESSION
    elif mutation == "wrong_originator":
        payload["originator"] = "codex_cli"
    elif mutation == "wrong_history_mode":
        payload["history_mode"] = "full"
    elif mutation == "wrong_cwd":
        payload["cwd"] = str(tmp_path / "other-work")
    elif mutation == "source_shape_drift":
        source["other"] = {}
    elif mutation == "agent_metadata_disagreement":
        spawn["agent_nickname"] = "Noether"
    elif mutation == "invalid_context_window":
        payload["context_window"] = {"window_id": CODEX_V1491_PARENT_SESSION}
    elif mutation == "noncausal_timestamp":
        payload["timestamp"] = "2026-08-27T05:24:23.389Z"
    else:  # pragma: no cover - the parameter list is closed above
        raise AssertionError(f"unhandled mutation: {mutation}")

    artifact = _codex_v1491_artifact(root, cwd=cwd, meta=meta)
    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


def test_codex_v1491_child_metadata_rejects_ambiguous_or_unbounded_json(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_artifact(root, cwd=cwd)
    line = json.dumps(_codex_v1491_meta(cwd=cwd))
    artifact.write_text(
        line.replace(
            '{"timestamp":',
            '{"timestamp":"2026-08-27T05:23:23.456Z","timestamp":',
            1,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )

    artifact.write_text(line, encoding="utf-8")
    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )

    oversized = _codex_v1491_meta(cwd=cwd)
    oversized_payload = oversized["payload"]
    assert isinstance(oversized_payload, dict)
    base = oversized_payload["base_instructions"]
    assert isinstance(base, dict)
    base["text"] = "x" * (128 * 1024)
    _codex_v1491_artifact(root, cwd=cwd, meta=oversized)
    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


def test_codex_v1491_child_metadata_rejects_foreign_shape_and_links(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    foreign = _write_jsonl(
        tmp_path / "foreign" / f"rollout-2026-08-27T05-23-23-{CODEX_V1491_CHILD_SESSION}.jsonl",
        [_codex_v1491_meta(cwd=cwd)],
    )
    assert (
        codex_v1491_child_parent_session(
            foreign,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )

    wrong_suffix = _write_jsonl(
        root / "2026" / "08" / "27" / f"rollout-2026-08-27T05-23-23-{CODEX_V1491_WINDOW_ID}.jsonl",
        [_codex_v1491_meta(cwd=cwd)],
    )
    assert (
        codex_v1491_child_parent_session(
            wrong_suffix,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )

    if os.name == "nt":
        return
    target = _write_jsonl(tmp_path / "target.jsonl", [_codex_v1491_meta(cwd=cwd)])
    linked = (
        root
        / "2026"
        / "08"
        / "27"
        / f"rollout-2026-08-27T05-23-23-{CODEX_V1491_CHILD_SESSION}.jsonl"
    )
    linked.parent.mkdir(parents=True, exist_ok=True)
    linked.symlink_to(target)
    assert (
        codex_v1491_child_parent_session(
            linked,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


def test_codex_v1491_child_metadata_requires_owner_integrity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "sessions"
    cwd = tmp_path / "canary-work"
    cwd.mkdir()
    artifact = _codex_v1491_artifact(root, cwd=cwd)
    monkeypatch.setattr(
        subject,
        "storage_artifact_parent_is_trusted",
        lambda *_args, **_kwargs: False,
    )

    assert (
        codex_v1491_child_parent_session(
            artifact,
            child_id=CODEX_V1491_CHILD_SESSION,
            cwd=cwd,
            root=root,
        )
        == ""
    )


def _v6_envelope(
    task: str,
    *,
    host: str = "claude",
    child_id: str = CHILD_AGENT,
    nonce: str = "nonce-unique-1",
    issued_at: str = ISSUED_AT,
    expires_at: str = EXPIRES_AT,
) -> str:
    return render_inference_team_delivery(
        task,
        (
            InferenceTeamCard(
                specialist_slug="database-engineer",
                specialist_version=content_digest(PROMPT),
                specialist_prompt_hash=content_digest(PROMPT),
                prompt_body=PROMPT,
            ),
            InferenceTeamCard(
                specialist_slug="security-auditor",
                specialist_version=content_digest(OTHER_PROMPT),
                specialist_prompt_hash=content_digest(OTHER_PROMPT),
                prompt_body=OTHER_PROMPT,
            ),
        ),
        host=host,
        parent_session_id=PARENT_SESSION,
        parent_trace_id="trace-9f2c",
        launch_id="launch-01ABC",
        decision_id="decision-inference-1",
        provider_receipt_digest=content_digest("provider-receipt"),
        candidate_digest=RUNTIME_DIGEST,
        install_id="install-1",
        bundle_digest=content_digest("bundle"),
        runtime_digest=RUNTIME_DIGEST,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
        binding_kind="child_id",
        binding_id=child_id,
    )


def _expected_from_diagnostic(
    evidence: subject.ChildDeliveryEvidence,
    **overrides: object,
) -> _ExpectedChildDelivery:
    values: dict[str, object] = {
        "host": evidence.host,
        "parent_session_id": evidence.envelope_parent_id,
        "parent_trace_id": evidence.parent_trace_id,
        "launch_id": evidence.launch_id,
        "child_id": evidence.child_id,
        "decision_id": evidence.decision_id,
        "provider_receipt_digest": evidence.provider_receipt_digest,
        "task_sha256": evidence.task_sha256,
        "team_digest": evidence.team_digest,
        "candidate_digest": evidence.candidate_digest,
        "install_id": evidence.install_id,
        "bundle_digest": evidence.bundle_digest,
        "runtime_digest": evidence.runtime_digest,
        "issued_at": evidence.issued_at,
        "expires_at": evidence.expires_at,
        "nonce": evidence.nonce,
        "binding_kind": evidence.binding_kind,
        "binding_id": evidence.binding_id,
        "cards": evidence.cards,
        "artifact_digest": evidence.artifact_digest,
    }
    values.update(overrides)
    return _ExpectedChildDelivery(**values)  # type: ignore[arg-type]


def _persisted_store_from_diagnostic(
    evidence: subject.ChildDeliveryEvidence,
    *,
    artifact_digest: str | None = None,
) -> object:
    """Return a read-only Store seam for one already-consumed exact receipt."""

    digest = artifact_digest or evidence.artifact_digest
    decision = {
        "decision_id": evidence.decision_id,
        "host": evidence.host,
        "parent_session_id": evidence.envelope_parent_id,
        "parent_trace_id": evidence.parent_trace_id,
        "launch_id": evidence.launch_id,
        "provider_receipt_digest": evidence.provider_receipt_digest,
        "task_sha256": evidence.task_sha256,
        "team_digest": evidence.team_digest,
        "candidate_digest": evidence.candidate_digest,
        "install_id": evidence.install_id,
        "bundle_digest": evidence.bundle_digest,
        "runtime_digest": evidence.runtime_digest,
        "issued_at": evidence.issued_at,
        "expires_at": evidence.expires_at,
        "nonce": evidence.nonce,
        "binding_kind": evidence.binding_kind,
        "binding_id": evidence.binding_id,
        "cards": [
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": card.body_character_length,
            }
            for card in evidence.cards
        ],
    }
    receipt = {
        "verified_delivery": True,
        "decision_id": evidence.decision_id,
        "nonce": evidence.nonce,
        "artifact_digest": digest,
        "host": evidence.host,
        "parent_session_id": evidence.envelope_parent_id,
        "parent_trace_id": evidence.parent_trace_id,
        "launch_id": evidence.launch_id,
        "binding_kind": evidence.binding_kind,
        "binding_id": evidence.binding_id,
        "child_id": evidence.child_id,
    }

    class StoreLike:
        def get_native_child_staffing_decision(self, decision_id: str) -> object:
            return decision if decision_id == evidence.decision_id else None

        def get_native_child_delivery_verification(self, decision_id: str) -> object:
            return receipt if decision_id == evidence.decision_id else None

    return StoreLike()


def test_a_legacy_launch_record_is_diagnostic_not_verified_delivery(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(tmp_path, [_claude_record(_envelope("Audit the schema."))])

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.staffed is False
    assert evidence.verified_delivery is False
    assert evidence.verification_reason == "legacy_delivery_non_authoritative"
    assert evidence.host == "claude"
    assert evidence.child_id == CHILD_AGENT
    assert [card.specialist_slug for card in evidence.cards] == ["database-engineer"]
    assert evidence.cards[0].specialist_prompt_hash == content_digest(PROMPT)


def test_the_envelope_is_correlated_against_the_host_written_parent(
    tmp_path: Path,
    private_root: None,
) -> None:
    """Agency wrote the envelope; Claude wrote ``sessionId``. Agreement is the proof."""

    artifact = _claude_artifact(tmp_path, [_claude_record(_envelope("Audit the schema."))])

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.host_parent_id == PARENT_SESSION
    assert evidence.envelope_parent_id == PARENT_SESSION
    assert evidence.correlated is True


def test_an_envelope_naming_another_parent_is_reported_uncorrelated(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_envelope("Audit the schema.", parent_session_id="another-session"))],
    )

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.staffed is False
    assert evidence.correlated is False


def test_a_marker_the_child_read_back_later_is_not_a_delivery(
    tmp_path: Path,
    private_root: None,
) -> None:
    """The false positive that would make this whole module worthless.

    Agents in this repository grep these literals out of the source constantly.
    A marker in a later record is the child reading about Agency, not Agency
    staffing the child.
    """

    artifact = _claude_artifact(
        tmp_path,
        [
            _claude_record("Audit the schema."),
            _claude_record(_envelope("grep output"), record_type="assistant"),
        ],
    )

    assert claude_child_delivery_evidence(artifact) is None


def test_a_parent_transcript_is_never_child_evidence(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_envelope("Audit the schema."), sidechain=False)],
    )

    assert claude_child_delivery_evidence(artifact) is None


def test_a_tampered_prompt_body_fails_its_own_pinned_identity(
    tmp_path: Path,
    private_root: None,
) -> None:
    delivered = _envelope("Audit the schema.")
    artifact = _claude_artifact(tmp_path, [_claude_record(delivered.replace("WAL", "WAL!"))])

    assert claude_child_delivery_evidence(artifact) is None


def test_every_delivered_card_is_recovered_in_delivery_order(
    tmp_path: Path,
    private_root: None,
) -> None:
    both = _envelope(_envelope("Audit the schema."), OTHER_PROMPT, slug="security-auditor")
    artifact = _claude_artifact(tmp_path, [_claude_record(both)])

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert [card.specialist_slug for card in evidence.cards] == [
        "database-engineer",
        "security-auditor",
    ]


def test_block_structured_message_content_is_read(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record([{"type": "text", "text": _envelope("Audit the schema.")}])],
    )

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.staffed is False


def test_a_long_transcript_still_yields_its_launch_record(
    tmp_path: Path,
    private_root: None,
) -> None:
    """Real sub-agent transcripts run to megabytes; only the head is evidence."""

    filler = _claude_record("x" * 4096, record_type="assistant")
    records = [_claude_record(_envelope("Audit the schema."))]
    records.extend(filler for _ in range(MAX_LAUNCH_PREFIX_BYTES // 4096 + 8))
    artifact = _claude_artifact(tmp_path, records)

    assert artifact.stat().st_size > MAX_LAUNCH_PREFIX_BYTES
    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.staffed is False


def test_a_codex_child_rollout_proves_the_child_received_the_card(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message(_envelope("Audit the schema.", host="codex")),
        ],
    )

    evidence = codex_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.host == "codex"
    assert evidence.host_parent_id == PARENT_SESSION
    assert evidence.correlated is True
    assert [card.specialist_slug for card in evidence.cards] == ["database-engineer"]


def test_a_codex_root_thread_is_not_a_spawned_child(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=False),
            _codex_message(_envelope("Audit the schema.", host="codex")),
        ],
    )

    assert codex_child_delivery_evidence(artifact) is None


def test_codex_text_after_the_child_speaks_is_not_delivery(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message("Working on it.", role="assistant"),
            _codex_message(_envelope("grep output", host="codex")),
        ],
    )

    assert codex_child_delivery_evidence(artifact) is None


def test_codex_reasoning_stops_the_scan_before_any_later_marker(
    tmp_path: Path,
    private_root: None,
) -> None:
    """Reasoning is the child working. A verifier may miss evidence, never invent it."""

    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            {"type": "response_item", "payload": {"type": "reasoning", "summary": []}},
            _codex_message(_envelope("grep output", host="codex")),
        ],
    )

    assert codex_child_delivery_evidence(artifact) is None


def test_v6_team_and_arbitrary_consumer_remain_diagnostic_only(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_v6_envelope("Audit the schema."))],
    )

    diagnostic = claude_child_delivery_evidence(artifact)

    assert diagnostic is not None
    assert diagnostic.v6_delivery is True
    assert diagnostic.verified_delivery is False
    assert diagnostic.staffed is False
    assert diagnostic.verification_reason == "host_hook_output_origin_not_proven"
    assert [card.specialist_slug for card in diagnostic.cards] == [
        "database-engineer",
        "security-auditor",
    ]

    expected = _expected_from_diagnostic(diagnostic)

    def consume(request: dict[str, object]) -> dict[str, object]:
        return {
            "verified_delivery": True,
            "decision_id": request["decision_id"],
            "nonce": request["nonce"],
            "artifact_digest": request["artifact_digest"],
        }

    verified = _verify_child_delivery_evidence(
        artifact,
        host="claude",
        expected=expected,
        verification_consumer=consume,
    )

    assert verified is not None
    assert verified.verified_delivery is False
    assert verified.staffed is False
    assert verified.verification_reason == "atomic_verification_consumer_not_supplied"


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"parent_session_id": "other-parent"}, "expected_decision_mismatch"),
        ({"parent_trace_id": "other-trace"}, "expected_decision_mismatch"),
        ({"launch_id": "other-launch"}, "expected_decision_mismatch"),
        ({"decision_id": "other-decision"}, "expected_decision_mismatch"),
        ({"install_id": "other-install"}, "expected_decision_mismatch"),
        ({"candidate_digest": content_digest("other")}, "expected_decision_mismatch"),
        ({"artifact_digest": content_digest("other-artifact")}, "artifact_digest_mismatch"),
    ],
)
def test_v6_expected_decision_tampering_never_verifies(
    tmp_path: Path,
    private_root: None,
    override: dict[str, object],
    reason: str,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_v6_envelope("Audit the schema."))],
    )
    diagnostic = claude_child_delivery_evidence(artifact)
    assert diagnostic is not None
    expected = _expected_from_diagnostic(diagnostic, **override)

    evidence = claude_child_delivery_evidence(
        artifact,
        expected_deliveries={CHILD_AGENT: expected},
    )

    assert evidence is not None
    assert evidence.verified_delivery is False
    assert evidence.staffed is False
    assert evidence.verification_reason == reason


@pytest.mark.parametrize(
    ("consumer", "reason"),
    [
        (None, "atomic_verification_consumer_not_supplied"),
        (lambda _request: False, "atomic_verification_consumer_not_supplied"),
        (lambda _request: 1, "atomic_verification_consumer_not_supplied"),
    ],
)
def test_exact_expected_delivery_needs_an_exact_atomic_consumer_receipt(
    tmp_path: Path,
    private_root: None,
    consumer: object,
    reason: str,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_v6_envelope("Audit the schema."))],
    )
    diagnostic = claude_child_delivery_evidence(artifact)
    assert diagnostic is not None

    evidence = claude_child_delivery_evidence(
        artifact,
        expected_deliveries={CHILD_AGENT: _expected_from_diagnostic(diagnostic)},
        verification_consumer=consumer,  # type: ignore[arg-type]
    )

    assert evidence is not None
    assert evidence.staffed is False
    assert evidence.verification_reason == reason


def test_store_consumer_adapter_passes_only_the_atomic_ledger_contract() -> None:
    observed: dict[str, object] = {}

    class StoreLike:
        def _record_native_child_delivery_verification(self, **kwargs: object) -> dict[str, object]:
            observed.update(kwargs)
            return {
                "verified_delivery": True,
                "decision_id": kwargs["decision_id"],
                "nonce": kwargs["nonce"],
                "artifact_digest": kwargs["artifact_digest"],
            }

    request = {
        "decision_id": "decision-1",
        "nonce": "nonce-1",
        "artifact_digest": "a" * 64,
        "host": "claude",
        "parent_session_id": "parent",
        "parent_trace_id": "trace",
        "launch_id": "launch",
        "binding_kind": "child_id",
        "binding_id": "child",
        "child_id": "child",
        "cards": [{"specialist_slug": "code-reviewer"}],
        "pre_speech": True,
        "structural_hook_output": False,
    }

    result = subject._store_native_child_delivery_consumer(StoreLike())(request)

    assert isinstance(result, dict) and result["verified_delivery"] is True
    assert set(observed) == {
        "decision_id",
        "nonce",
        "artifact_digest",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "binding_kind",
        "binding_id",
        "child_id",
        "cards",
    }


def test_real_store_consumer_atomically_verifies_then_rejects_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    private_root: None,
    canonical_roots: None,
    collector_lease,
) -> None:
    from agency_runtime.core.store.sqlite import Store

    task = "Audit the schema."
    issued = datetime.now(timezone.utc).replace(microsecond=0)
    issued_at = issued.isoformat(timespec="seconds").replace("+00:00", "Z")
    observed_at = (
        (issued + timedelta(seconds=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    expires_at = (
        (issued + timedelta(minutes=5)).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    team = (
        InferenceTeamCard(
            specialist_slug="database-engineer",
            specialist_version=content_digest(PROMPT),
            specialist_prompt_hash=content_digest(PROMPT),
            prompt_body=PROMPT,
        ),
        InferenceTeamCard(
            specialist_slug="security-auditor",
            specialist_version=content_digest(OTHER_PROMPT),
            specialist_prompt_hash=content_digest(OTHER_PROMPT),
            prompt_body=OTHER_PROMPT,
        ),
    )
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
    provider_digest = canonical_native_child_provider_receipt_digest(attempts)
    assert provider_digest is not None
    cards = [
        {
            "specialist_slug": card.specialist_slug,
            "specialist_version": card.specialist_version,
            "specialist_prompt_hash": card.specialist_prompt_hash,
            "body_character_length": len(card.prompt_body),
        }
        for card in team
    ]
    decision_payload = {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "claude",
        "parent_session_id": PARENT_SESSION,
        "parent_trace_id": "trace-9f2c",
        "launch_id": "launch-01ABC",
        "binding_kind": "child_id",
        "binding_id": CHILD_AGENT,
        "provider_attempts": attempts,
        "provider_receipt_digest": provider_digest,
        "task_sha256": content_digest(task),
        "team_digest": inference_team_digest(team),
        "candidate_digest": RUNTIME_DIGEST,
        "runtime_digest": RUNTIME_DIGEST,
        "install_id": "install-1",
        "bundle_digest": content_digest("bundle"),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": "nonce-unique-1",
        "cards": cards,
    }
    store = Store(tmp_path / "agency.db")
    store.create_run(
        session_id=PARENT_SESSION,
        trace_id="trace-9f2c",
        host="claude",
        user_message=task,
    )
    decision_id = store.record_routing_decision(
        trace_id="trace-9f2c",
        session_id=PARENT_SESSION,
        query_hash=content_digest(task),
        context_fingerprint=content_digest("context"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": [card.specialist_slug for card in team],
            "semantic_ids": [card.specialist_slug for card in team],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": len(team),
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": content_digest(task),
            "query_hash": content_digest(task),
            "context_fingerprint": content_digest("context"),
            "native_child_delivery": decision_payload,
        },
    )
    collection = _begin_private_host_artifact_collection(collector_lease, host="claude")
    monkeypatch.setattr(subject, "default_child_artifact_root", lambda _host: collection.root)
    delivered = render_inference_team_delivery(
        task,
        team,
        host="claude",
        parent_session_id=PARENT_SESSION,
        parent_trace_id="trace-9f2c",
        launch_id="launch-01ABC",
        decision_id=decision_id,
        provider_receipt_digest=provider_digest,
        candidate_digest=RUNTIME_DIGEST,
        install_id="install-1",
        bundle_digest=content_digest("bundle"),
        runtime_digest=RUNTIME_DIGEST,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce="nonce-unique-1",
        binding_kind="child_id",
        binding_id=CHILD_AGENT,
    )
    invocation_start = _start_private_host_invocation(collection)
    artifact = _claude_artifact(
        collection.root,
        [_claude_record(delivered, timestamp=observed_at)],
    )
    invocation = _finish_private_host_invocation(invocation_start)
    diagnostic = claude_child_delivery_evidence(artifact)
    assert diagnostic is not None
    collected = _collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=store,
    )
    assert collected.reason == "collected"
    capability = collected.proof
    assert capability is not None
    verified = capability.evidence
    proof = _consume_verified_host_child_delivery(capability)

    assert verified is not None and verified.staffed is True
    assert verified.verification_reason == "verified"
    assert proof is not None and proof["decision_id"] == decision_id
    assert _consume_verified_host_child_delivery(capability) is None
    receipt = store.get_native_child_delivery_verification(decision_id)
    assert receipt is not None
    assert receipt["artifact_digest"] == verified.artifact_digest
    assert store.list_native_child_delivery_verifications(host="claude", limit=1) == [receipt]

    projection = child_delivery_projection(
        collection.root,
        host="claude",
        limit=1,
        store=store,
    )
    assert projection["staffed_children"] == 1
    assert projection["children"][0]["verification_reason"] == "verified_existing_receipt"

    swapped_record = _claude_record(delivered, timestamp=observed_at)
    swapped_record["agentId"] = "other-child"
    swapped_child = _write_jsonl(
        tmp_path / "swapped" / PARENT_SESSION / "subagents" / "agent-other-child.jsonl",
        [swapped_record],
    )
    swapped_diagnostic = claude_child_delivery_evidence(swapped_child)
    assert swapped_diagnostic is not None
    child_mismatch = subject._verify_against_persisted_receipt(
        swapped_child,
        host="claude",
        diagnostic=swapped_diagnostic,
        store=store,
    )
    assert child_mismatch is not None and child_mismatch.staffed is False
    assert child_mismatch.verification_reason == "child_or_launch_binding_invalid"

    # The persisted receipt identifies the exact bounded artifact bytes. A
    # parseable mutation must not inherit the old artifact's green status.
    artifact.write_text(artifact.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    changed_diagnostic = claude_child_delivery_evidence(artifact)
    assert changed_diagnostic is not None
    changed = subject._verify_against_persisted_receipt(
        artifact,
        host="claude",
        diagnostic=changed_diagnostic,
        store=store,
    )
    assert changed is not None and changed.staffed is False
    assert changed.verification_reason == "atomic_verification_consumer_rejected"


def test_codex_parser_preserves_opaque_channel_failure_without_store_authority(
    tmp_path: Path,
    private_root: None,
    canonical_roots: None,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [_codex_meta(spawned=True), _codex_message(_v6_envelope("Review.", host="codex"))],
    )

    evidence = codex_child_delivery_evidence(artifact)

    assert evidence is not None and evidence.staffed is False
    assert evidence.verification_reason == "unsupported_opaque_interagent_channel"


def test_restricted_codex_structural_reader_requires_store_consumption(
    tmp_path: Path,
    private_root: None,
) -> None:
    message = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    message["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(
        tmp_path,
        [_codex_meta(spawned=True), message, _codex_message("Completed.", role="assistant")],
    )
    diagnostic = codex_child_delivery_evidence(artifact)
    assert diagnostic is not None
    assert diagnostic.verification_reason == "unsupported_opaque_interagent_channel"

    class StoreLike:
        def _record_native_child_delivery_verification(
            self,
            **kwargs: object,
        ) -> dict[str, object]:
            return {**kwargs, "verified_delivery": True}

    verified = _verify_child_delivery_evidence(
        artifact,
        host="codex",
        expected=_expected_from_diagnostic(diagnostic),
        verification_consumer=subject._store_native_child_delivery_consumer(StoreLike()),
        structural_hook_output=True,
    )

    assert verified is not None
    assert verified.staffed is True
    assert verified.verification_reason == "verified"


def test_persisted_codex_receipt_replays_its_exact_prefix_after_host_append(
    tmp_path: Path,
    private_root: None,
) -> None:
    message = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    message["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(
        tmp_path,
        [_codex_meta(spawned=True), message, _codex_message("Completed.", role="assistant")],
    )
    receipt_evidence = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert receipt_evidence is not None
    store = _persisted_store_from_diagnostic(receipt_evidence)

    with artifact.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}))
        stream.write("\n")
    completed = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert completed is not None
    assert completed.artifact_digest != receipt_evidence.artifact_digest

    replayed = subject._verify_against_persisted_receipt(
        artifact,
        host="codex",
        diagnostic=completed,
        store=store,
        structural_hook_output=True,
    )

    assert replayed.staffed is True
    assert replayed.verification_reason == "verified_existing_receipt"
    assert replayed.artifact_digest == receipt_evidence.artifact_digest


def test_persisted_codex_receipt_rejects_a_changed_verified_prefix(
    tmp_path: Path,
    private_root: None,
) -> None:
    message = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    message["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(tmp_path, [_codex_meta(spawned=True), message])
    receipt_evidence = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert receipt_evidence is not None
    store = _persisted_store_from_diagnostic(receipt_evidence)

    changed = artifact.read_text(encoding="utf-8").replace(
        "2026-08-01T04:18:04.132Z",
        "2026-08-01T04:18:04.133Z",
        1,
    )
    artifact.write_text(changed, encoding="utf-8")
    diagnostic = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert diagnostic is not None

    replayed = subject._verify_against_persisted_receipt(
        artifact,
        host="codex",
        diagnostic=diagnostic,
        store=store,
        structural_hook_output=True,
    )

    assert replayed.staffed is False
    assert replayed.verification_reason == "persisted_artifact_prefix_invalid"


def test_persisted_codex_receipt_digest_must_end_at_a_jsonl_record_boundary(
    tmp_path: Path,
    private_root: None,
) -> None:
    message = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    message["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(tmp_path, [_codex_meta(spawned=True), message])
    diagnostic = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert diagnostic is not None
    partial_digest = sha256(artifact.read_bytes()[:-1]).hexdigest()
    store = _persisted_store_from_diagnostic(diagnostic, artifact_digest=partial_digest)

    replayed = subject._verify_against_persisted_receipt(
        artifact,
        host="codex",
        diagnostic=diagnostic,
        store=store,
        structural_hook_output=True,
    )

    assert replayed.staffed is False
    assert replayed.verification_reason == "persisted_artifact_prefix_invalid"


def test_persisted_codex_receipt_rejects_a_truncated_verified_prefix(
    tmp_path: Path,
    private_root: None,
) -> None:
    message = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    message["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(tmp_path, [_codex_meta(spawned=True), message])
    diagnostic = subject._codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    assert diagnostic is not None
    artifact.write_bytes(artifact.read_bytes()[:-1])

    assert (
        subject._trusted_launch_material(
            artifact,
            label="truncated Codex receipt fixture",
            artifact_parent=True,
            required_prefix_digest=diagnostic.artifact_digest,
        )
        is None
    )


def test_restricted_codex_structural_reader_rejects_multiple_v6_records(
    tmp_path: Path,
    private_root: None,
) -> None:
    valid = _codex_message(_v6_envelope("Review.", host="codex", child_id=CODEX_CHILD_SESSION))
    valid["timestamp"] = OBSERVED_AT
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message("[AGENCY INFERENCE TEAM v6]\npartial"),
            valid,
            _codex_message("Completed.", role="assistant"),
        ],
    )

    assert (
        subject._codex_child_delivery_evidence(
            artifact,
            structural_hook_output=True,
        )
        is None
    )


def test_v6_stale_host_event_never_verifies(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [
            _claude_record(
                _v6_envelope("Audit the schema."),
                timestamp="2026-08-09T00:06:00Z",
            )
        ],
    )
    diagnostic = claude_child_delivery_evidence(artifact)
    assert diagnostic is not None

    evidence = claude_child_delivery_evidence(
        artifact,
        expected_deliveries={CHILD_AGENT: _expected_from_diagnostic(diagnostic)},
    )

    assert evidence is not None
    assert evidence.verification_reason == "decision_time_window_invalid"
    assert evidence.staffed is False


@pytest.mark.parametrize("mutation", ["tampered", "partial", "mixed", "spliced"])
def test_v6_team_is_atomic_and_never_salvages_a_partial_or_mixed_delivery(
    tmp_path: Path,
    private_root: None,
    mutation: str,
) -> None:
    delivered = _v6_envelope("Audit the schema.")
    if mutation == "tampered":
        delivered = delivered.replace("Prefer WAL", "Prefer rollback", 1)
    elif mutation == "partial":
        delivered = delivered.rsplit("<!-- agency-native-child-team-end:v6:", 1)[0]
    elif mutation == "mixed":
        delivered += _envelope("legacy suffix")
    else:
        delivered += _v6_envelope("Other task.", nonce="nonce-unique-2")
    artifact = _claude_artifact(tmp_path, [_claude_record(delivered)])

    assert claude_child_delivery_evidence(artifact) is None


def test_codex_0147_v6_marker_remains_explicitly_unsupported(
    tmp_path: Path,
    private_root: None,
) -> None:
    child_id = CODEX_CHILD_SESSION
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message(_v6_envelope("Audit the schema.", host="codex", child_id=child_id)),
        ],
    )
    diagnostic = codex_child_delivery_evidence(artifact)
    assert diagnostic is not None
    expected = _expected_from_diagnostic(diagnostic)

    evidence = codex_child_delivery_evidence(
        artifact,
        expected_deliveries={child_id: expected},
    )

    assert evidence is not None
    assert evidence.v6_delivery is True
    assert evidence.verified_delivery is False
    assert evidence.staffed is False
    assert evidence.verification_reason == "unsupported_opaque_interagent_channel"


def test_codex_full_meta_and_filename_identity_is_canonical_but_unsupported(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message(
                _v6_envelope("Audit the schema.", host="codex", child_id=CODEX_CHILD_SESSION)
            ),
        ],
    )

    evidence = codex_child_delivery_evidence(artifact)

    assert evidence is not None
    assert subject._canonical_host_artifact_is_trusted(
        artifact,
        host="codex",
        root=tmp_path,
        evidence=evidence,
    )
    assert evidence.verification_reason == "unsupported_opaque_interagent_channel"


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode regression")
def test_codex_normal_umask_artifact_keeps_integrity_without_private_date_dirs(
    tmp_path: Path,
) -> None:
    artifact = _codex_artifact(
        tmp_path,
        [
            _codex_meta(spawned=True),
            _codex_message(
                _v6_envelope("Audit the schema.", host="codex", child_id=CODEX_CHILD_SESSION)
            ),
        ],
    )
    for parent in artifact.parents[:3]:
        parent.chmod(0o755)
    artifact.chmod(0o644)

    evidence = codex_child_delivery_evidence(artifact)

    assert evidence is not None
    assert subject._canonical_host_artifact_is_trusted(
        artifact,
        host="codex",
        root=tmp_path,
        evidence=evidence,
    )

    artifact.parent.chmod(0o775)
    artifact.chmod(0o664)
    assert codex_child_delivery_evidence(artifact) is not None

    artifact.parent.chmod(0o777)
    assert codex_child_delivery_evidence(artifact) is None


def test_codex_truncated_filename_is_noncanonical_and_never_consults_store(
    tmp_path: Path,
    private_root: None,
    canonical_roots: None,
) -> None:
    truncated = "019fbb8b-1394-7413"
    artifact = _write_jsonl(
        tmp_path / "2026" / "08" / "01" / f"rollout-2026-08-01T00-18-01-{truncated}.jsonl",
        [
            _codex_meta(spawned=True),
            _codex_message(
                _v6_envelope("Audit the schema.", host="codex", child_id=CODEX_CHILD_SESSION)
            ),
        ],
    )
    calls: list[str] = []

    class StoreLike:
        def get_native_child_staffing_decision(self, _decision_id: str) -> object:
            calls.append("decision")
            raise AssertionError("noncanonical Codex artifacts must not consult the Store")

        def get_native_child_delivery_verification(self, _decision_id: str) -> object:
            calls.append("receipt")
            raise AssertionError("noncanonical Codex artifacts must not consult the Store")

    evidence = codex_child_delivery_evidence(artifact)
    projection = child_delivery_projection(
        tmp_path,
        host="codex",
        limit=1,
        store=StoreLike(),
    )

    assert evidence is not None
    assert not subject._canonical_host_artifact_is_trusted(
        artifact,
        host="codex",
        root=tmp_path,
        evidence=evidence,
    )
    assert projection["children"][0]["verification_reason"] == "artifact_origin_not_canonical"
    assert calls == []


def test_collector_refuses_even_an_empty_caller_lookalike_root(
    tmp_path: Path,
    private_root: None,
) -> None:
    lookalike = tmp_path / "claude" / "projects"
    lookalike.mkdir(parents=True)

    with pytest.raises(ValueError, match="active private temporary lease"):
        subject._begin_private_host_artifact_collection(lookalike, host="claude")  # type: ignore[arg-type]


def test_private_file_outside_collector_scope_cannot_reach_store(
    tmp_path: Path,
    private_root: None,
    collector_lease,
) -> None:
    collection = subject._begin_private_host_artifact_collection(
        collector_lease,
        host="claude",
    )
    invocation_start = subject._start_private_host_invocation(collection)
    _claude_artifact(
        tmp_path / "outside",
        [_claude_record(_v6_envelope("Audit the schema."))],
    )
    invocation = subject._finish_private_host_invocation(invocation_start)

    class StoreLike:
        def get_native_child_staffing_decision(self, _decision_id: str) -> object:
            raise AssertionError("out-of-scope artifacts must not consult the Store")

        def get_native_child_delivery_verification(self, _decision_id: str) -> object:
            raise AssertionError("out-of-scope artifacts must not consult the Store")

    collected = subject._collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=StoreLike(),
    )
    assert collected.proof is None
    # The private namespace stayed empty: the artifact was written outside it.
    assert collected.reason == "no_child_artifact"


def test_copied_historical_artifact_cannot_enter_current_invocation_window(
    monkeypatch: pytest.MonkeyPatch,
    private_root: None,
    collector_lease,
) -> None:
    collection = subject._begin_private_host_artifact_collection(
        collector_lease,
        host="claude",
    )
    invocation_start = subject._start_private_host_invocation(collection)
    historical = _v6_envelope(
        "Audit the schema.",
        issued_at="2026-08-09T00:00:00Z",
        expires_at="2026-08-09T00:05:00Z",
    )
    _claude_artifact(
        collection.root,
        [_claude_record(historical, timestamp="2026-08-09T00:00:01Z")],
    )
    invocation = subject._finish_private_host_invocation(invocation_start)
    monkeypatch.setattr(
        subject,
        "_verify_child_delivery_with_capability",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stale artifacts must fail before Store verification")
        ),
    )

    collected = subject._collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=object(),
    )
    assert collected.proof is None
    # The file was written now, so its mtime is current; the host-authored event
    # inside it is a week old, which is the copy this guard exists to refuse.
    assert collected.reason == "child_event_outside_invocation_window"


def _extra_claude_artifact(root: Path, child_id: str, text: object) -> Path:
    record = _claude_record(text)
    record["agentId"] = child_id
    return _write_jsonl(
        root / "proj" / PARENT_SESSION / "subagents" / f"agent-{child_id}.jsonl",
        [record],
    )


def test_collection_reason_vocabulary_is_closed_and_agrees_with_the_proof() -> None:
    assert "collected" in subject.HOST_CHILD_COLLECTION_REASONS
    with pytest.raises(ValueError, match="bounded vocabulary"):
        subject.HostChildCollection(proof=None, reason="something_new")
    with pytest.raises(ValueError, match="does not agree"):
        subject.HostChildCollection(proof=None, reason="collected")


def test_a_host_that_fans_out_to_several_children_says_so(
    private_root: None,
    collector_lease,
) -> None:
    """Four children is the shape a real canary produced on 2026-08-14.

    Collection still refuses -- "the artifact this invocation wrote" has no
    single answer -- but a fan-out must not be indistinguishable from a host
    that spawned nothing at all.
    """

    collection = subject._begin_private_host_artifact_collection(collector_lease, host="claude")
    invocation_start = subject._start_private_host_invocation(collection)
    _claude_artifact(collection.root, [_claude_record(_v6_envelope("Audit the schema."))])
    _extra_claude_artifact(collection.root, "a538d7182969e4855", "List the files.")
    invocation = subject._finish_private_host_invocation(invocation_start)

    collected = subject._collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=object(),
    )

    assert collected.proof is None
    assert collected.reason == "multiple_child_artifacts"


def test_a_child_that_received_no_card_is_named_as_such(
    private_root: None,
    collector_lease,
) -> None:
    """The live failure: a well-formed child transcript with no Agency marker."""

    collection = subject._begin_private_host_artifact_collection(collector_lease, host="claude")
    invocation_start = subject._start_private_host_invocation(collection)
    _claude_artifact(collection.root, [_claude_record("Review the change and report.")])
    invocation = subject._finish_private_host_invocation(invocation_start)

    collected = subject._collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=object(),
    )

    assert collected.proof is None
    assert collected.reason == "delivery_marker_absent"


def test_a_legacy_envelope_is_refused_under_its_own_name(
    private_root: None,
    collector_lease,
) -> None:
    """Every marked child on the evidence workstation carries v5, not v6.

    A v5 envelope means a card *was* delivered, by a runtime that predates the
    Rule 4 authority. Reporting that as "no marker" would send the next reader
    looking for a staffing outage that is not there.
    """

    collection = subject._begin_private_host_artifact_collection(collector_lease, host="claude")
    invocation_start = subject._start_private_host_invocation(collection)
    _claude_artifact(collection.root, [_claude_record(_envelope("Audit the schema."))])
    invocation = subject._finish_private_host_invocation(invocation_start)

    collected = subject._collect_private_host_child_delivery(
        collection,
        invocation=invocation,
        store=object(),
    )

    assert collected.proof is None
    assert collected.reason == "legacy_delivery_not_authoritative"


def test_raw_diagnostic_and_forged_typed_value_cannot_project_authority(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(
        tmp_path,
        [_claude_record(_v6_envelope("Audit the schema."))],
    )
    diagnostic = claude_child_delivery_evidence(artifact)
    assert diagnostic is not None
    forged_diagnostic = replace(diagnostic, verified_delivery=True)

    assert subject._consume_verified_host_child_delivery(forged_diagnostic) is None
    with pytest.raises(TypeError, match="trusted collector"):
        subject._VerifiedHostChildDelivery(
            forged_diagnostic,
            _consumption_scope="single",
            _seal=object(),
        )


def test_collector_authority_is_absent_from_the_public_evidence_surface() -> None:
    assert {
        "_begin_private_host_artifact_collection",
        "_collect_private_host_child_delivery",
        "_VerifiedHostChildDelivery",
        "_consume_verified_host_child_delivery",
    }.isdisjoint(subject.__all__)


def test_arbitrary_consumer_cannot_authorize_original_or_replayed_artifact(
    tmp_path: Path,
    private_root: None,
) -> None:
    record = _claude_record(_v6_envelope("Audit the schema."))
    first = _claude_artifact(tmp_path, [record])
    replay = _write_jsonl(
        tmp_path / "proj" / PARENT_SESSION / "subagents" / "agent-replay.jsonl",
        [record],
    )
    diagnostic = claude_child_delivery_evidence(first)
    assert diagnostic is not None
    expected = _expected_from_diagnostic(diagnostic)

    def consume(request: dict[str, object]) -> object:
        return {
            "verified_delivery": True,
            "decision_id": request["decision_id"],
            "nonce": request["nonce"],
            "artifact_digest": request["artifact_digest"],
        }

    original = _verify_child_delivery_evidence(
        first,
        host="claude",
        expected=expected,
        verification_consumer=consume,
    )
    replayed = _verify_child_delivery_evidence(
        replay,
        host="claude",
        expected=expected,
        verification_consumer=consume,
    )

    assert original is not None and original.staffed is False
    assert original.verification_reason == "atomic_verification_consumer_not_supplied"
    assert replayed is not None and replayed.staffed is False
    assert replayed.verification_reason == "atomic_verification_consumer_not_supplied"


def test_unexpected_replay_copy_without_expected_decision_never_verifies(
    tmp_path: Path,
    private_root: None,
) -> None:
    original_record = _claude_record(_v6_envelope("Audit the schema."))
    first = _claude_artifact(tmp_path, [original_record])
    replay_record = dict(original_record)
    replay_record["agentId"] = "unexpected-child"
    _write_jsonl(
        tmp_path / "proj" / PARENT_SESSION / "subagents" / "agent-unexpected-child.jsonl",
        [replay_record],
    )
    diagnostic = claude_child_delivery_evidence(first)
    assert diagnostic is not None

    copied = claude_child_delivery_evidence(
        tmp_path / "proj" / PARENT_SESSION / "subagents" / "agent-unexpected-child.jsonl",
        expected_deliveries={CHILD_AGENT: _expected_from_diagnostic(diagnostic)},
    )

    assert copied is not None
    assert copied.staffed is False
    assert copied.verification_reason == "host_hook_output_origin_not_proven"


def test_scanning_a_root_reads_every_child_the_host_wrote(
    tmp_path: Path,
    private_root: None,
) -> None:
    _claude_artifact(tmp_path, [_claude_record(_envelope("Audit the schema."))])
    _write_jsonl(
        tmp_path / "proj" / PARENT_SESSION / "subagents" / "workflows" / "wf_1" / "agent-b2.jsonl",
        [_claude_record(_envelope("Review the hook."))],
    )

    findings = scan_child_delivery_evidence(tmp_path, host="claude")

    assert len(findings) == 2
    assert all(not finding.staffed for finding in findings)
    assert all(finding.legacy_delivery for finding in findings)


def test_projection_counts_the_window_and_returns_bounded_newest_proof(
    tmp_path: Path,
    private_root: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_CHILD_ARTIFACTS", 2)
    artifacts: list[Path] = []
    for index in range(3):
        record = _claude_record(_envelope(f"Audit schema {index}."))
        record["agentId"] = f"child-{index}"
        artifact = _write_jsonl(
            tmp_path / "proj" / PARENT_SESSION / "subagents" / f"agent-child-{index}.jsonl",
            [record],
        )
        os.utime(artifact, (1_700_000_000 + index, 1_700_000_000 + index))
        artifacts.append(artifact)

    projection = child_delivery_projection(tmp_path, host="claude", limit=1)

    assert projection["root_present"] is True
    assert projection["artifact_candidates"] == 3
    assert projection["artifact_candidate_count_complete"] is True
    assert projection["artifacts_scanned"] == 2
    assert projection["artifact_scan_truncated"] is True
    assert projection["filesystem_entries_visited"] <= subject.MAX_CHILD_FILESYSTEM_ENTRIES
    assert projection["evidence_count"] == 2
    assert projection["staffed_children"] == 0
    assert projection["correlated_staffed_children"] == 0
    assert projection["uncorrelated_staffed_children"] == 0
    assert projection["legacy_deliveries"] == 2
    assert projection["unverified_deliveries"] == 2
    assert projection["detail_limit"] == 1
    assert projection["detail_truncated"] is True
    assert projection["children"][0]["child_id"] == "child-2"
    assert projection["children"][0]["artifact"] == str(artifacts[2])
    assert projection["children"][0]["cards"] == []
    assert projection["children"][0]["diagnostic_cards"]


def test_unverified_v6_projection_is_not_mislabeled_as_legacy(
    tmp_path: Path,
    private_root: None,
) -> None:
    _claude_artifact(tmp_path, [_claude_record(_v6_envelope("Audit the schema."))])

    projection = child_delivery_projection(tmp_path, host="claude", limit=1)

    assert projection["legacy_deliveries"] == 0
    assert projection["unverified_deliveries"] == 1
    assert projection["children"][0]["legacy"] is False
    assert projection["children"][0]["v6"] is True


def test_host_tree_visits_are_bounded_and_candidate_count_is_a_lower_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_CHILD_FILESYSTEM_ENTRIES", 3)
    for index in range(8):
        (tmp_path / f"project-{index}").mkdir()

    projection = child_delivery_projection(tmp_path, host="claude", limit=50)

    assert projection["filesystem_entries_visited"] == 3
    assert projection["artifact_candidates"] == 0
    assert projection["artifact_candidate_count_complete"] is False
    assert projection["artifact_scan_truncated"] is True


def test_empty_projection_means_no_verified_proof_not_no_children(
    tmp_path: Path,
    private_root: None,
) -> None:
    _claude_artifact(tmp_path, [_claude_record("ordinary child prompt")])

    projection = child_delivery_projection(tmp_path, host="claude", limit=50)

    assert projection["artifact_candidates"] == 1
    assert projection["artifact_candidate_count_complete"] is True
    assert projection["artifacts_scanned"] == 1
    assert projection["evidence_count"] == 0
    assert projection["children"] == []


@pytest.mark.parametrize("limit", [0, 201, True])
def test_projection_rejects_an_unbounded_detail_limit(tmp_path: Path, limit: object) -> None:
    with pytest.raises(ValueError, match="between 1 and 200"):
        child_delivery_projection(tmp_path, host="claude", limit=limit)  # type: ignore[arg-type]


def test_cli_handler_does_not_turn_zero_detail_limit_into_the_default(tmp_path: Path) -> None:
    args = argparse.Namespace(host="claude", root=str(tmp_path), limit=0, json=True)

    with pytest.raises(ValueError, match="between 1 and 200"):
        cmd_evidence_children(args)


def test_cli_default_child_evidence_path_never_opens_the_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_opened(_db: object = None) -> object:
        raise AssertionError("default read-only evidence path opened the Store")

    monkeypatch.setattr(evidence_commands, "Store", fail_if_opened)

    assert (
        cmd_evidence_children(
            argparse.Namespace(
                host="claude",
                root=str(tmp_path),
                record_verification=None,
                db=None,
                limit=50,
                json=True,
            )
        )
        == 0
    )


def test_a_directory_other_accounts_can_write_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evidence read out of a substitutable directory is forged evidence.

    Asserted through the gate rather than through real ACLs: a POSIX temp
    directory is genuinely private, so the platforms would disagree about what
    this test even means.
    """

    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: False)
    artifact = _claude_artifact(tmp_path, [_claude_record(_envelope("Audit the schema."))])

    assert claude_child_delivery_evidence(artifact) is None


def test_an_unsupported_host_is_refused(tmp_path: Path) -> None:
    artifact = _claude_artifact(tmp_path, [_claude_record("hello")])

    with pytest.raises(ValueError, match="unsupported"):
        child_delivery_evidence(artifact, host="openclaw")


_ENC_PARENT = "01a052d1-7b63-7982-bf77-736c6713df46"
_ENC_CHILD = "01a052d2-0e59-77d2-9a48-a3d33edccad0"
_ENC_TOKEN = "gAAAAAB" + "q" * 300


def _encrypted_child_records(
    *,
    token: str = _ENC_TOKEN,
    parent: str = _ENC_PARENT,
    child: str = _ENC_CHILD,
) -> list[dict]:
    return [
        {
            "timestamp": "2026-08-30T14:07:55.590Z",
            "type": "session_meta",
            "payload": {
                "id": child,
                "timestamp": "2026-08-30T14:07:55.590Z",
                "cwd": "/home/holeshot/.agency-runtime/ephemeral/canary-x",
                "originator": "codex_exec",
                "cli_version": "0.151.0",
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": parent,
                            "depth": 1,
                            "agent_path": "/root/code_reviewer",
                            "agent_nickname": "Mill",
                            "agent_role": "Code Reviewer",
                        }
                    }
                },
            },
        },
        {
            "timestamp": "2026-08-30T14:07:55.600Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "id": "msg-dev-1",
                "content": [{"type": "input_text", "text": "# AGENTS.md instructions"}],
            },
        },
        {
            "timestamp": "2026-08-30T14:07:55.700Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "author": "/root",
                "recipient": "/root/code_reviewer",
                "id": "msg-new-task",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Message Type: NEW_TASK\nTask name: /root/code_reviewer\n"
                            "Sender: /root\nPayload: "
                        ),
                    },
                    {"type": "encrypted_content", "encrypted_content": token},
                ],
                "internal_chat_message_metadata_passthrough": {"turn_id": "t-1"},
            },
        },
        {
            "timestamp": "2026-08-30T14:08:01.000Z",
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "id": "msg-child-1",
                "content": [{"type": "text", "text": "Review complete."}],
            },
        },
    ]


def _encrypted_parent_records(
    *,
    token: str = _ENC_TOKEN,
    parent: str = _ENC_PARENT,
) -> list[dict]:
    return [
        {
            "timestamp": "2026-08-30T14:07:35.000Z",
            "type": "session_meta",
            "payload": {"id": parent, "cwd": "/home/holeshot"},
        },
        {
            "timestamp": "2026-08-30T14:07:55.500Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "id": "fc-1",
                "call_id": "call-1",
                "arguments": json.dumps(
                    {
                        "agent_type": "Code Reviewer",
                        "fork_turns": "none",
                        "message": token,
                        "task_name": "code_reviewer",
                    }
                ),
                "internal_chat_message_metadata_passthrough": {"turn_id": "t-0"},
            },
        },
        {
            "timestamp": "2026-08-30T14:07:55.950Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "id": "fco-1",
                "call_id": "call-1",
                "output": json.dumps({"task_name": "/root/code_reviewer"}),
            },
        },
    ]


def _write_encrypted_rollouts(root: Path) -> tuple[Path, Path]:
    day = root / "2026" / "08" / "30"
    day.mkdir(parents=True)
    child = day / f"rollout-2026-08-30T14-07-55-{_ENC_CHILD}.jsonl"
    parent = day / f"rollout-2026-08-30T14-07-35-{_ENC_PARENT}.jsonl"
    child.write_text(
        "".join(json.dumps(record) + "\n" for record in _encrypted_child_records()),
        encoding="utf-8",
    )
    parent.write_text(
        "".join(json.dumps(record) + "\n" for record in _encrypted_parent_records()),
        encoding="utf-8",
    )
    return child, parent


def _encrypted_route() -> dict:
    return {
        "decision_id": "native-child-abc123",
        "host": "codex",
        "parent_session_id": _ENC_PARENT,
        "parent_trace_id": "trace-enc-1",
        "launch_id": _ENC_CHILD,
        "binding_kind": "child_id",
        "binding_id": _ENC_CHILD,
        "provider_receipt_digest": "d" * 64,
        "task_sha256": "a" * 64,
        "team_digest": "b" * 64,
        "candidate_digest": "c" * 64,
        "runtime_digest": "e" * 64,
        "install_id": "install-1",
        "bundle_digest": "f" * 64,
        "issued_at": "2026-08-30T14:07:55Z",
        "expires_at": "2026-08-30T14:37:55Z",
        "nonce": "n" * 32,
        "cards": [
            {
                "specialist_slug": "code-reviewer",
                "specialist_version": "1.0.0",
                "specialist_prompt_hash": "9" * 64,
                "body_character_length": 512,
            }
        ],
    }


class _EncryptedDeliveryStore:
    def __init__(self) -> None:
        self.receipt: dict | None = None
        self.consumed: list[dict] = []

    def get_native_child_staffing_decision(self, _decision_id: str) -> None:
        return None

    def get_native_child_delivery_verification(self, _decision_id: str) -> dict | None:
        return self.receipt

    def _record_native_child_delivery_verification(self, **kwargs: object) -> dict:
        self.consumed.append(dict(kwargs))
        return {
            "verified_delivery": True,
            "decision_id": kwargs["decision_id"],
            "nonce": kwargs["nonce"],
            "artifact_digest": kwargs["artifact_digest"],
        }


def test_host_encrypted_canary_evidence_admits_byte_equal_task_delivery(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    # ADR-0194: the proof is byte equality between the parent's attested
    # spawn payload and the sole pre-speech NEW_TASK ciphertext, bound to the
    # Store decision through the one-use atomic consumer.
    root = tmp_path / "sessions"
    child, _parent = _write_encrypted_rollouts(root)
    store = _EncryptedDeliveryStore()

    evidence = subject._host_encrypted_canary_evidence(
        store,
        artifact=child,
        route=_encrypted_route(),
        child_id=_ENC_CHILD,
        parent_session_id=_ENC_PARENT,
        root=root,
    )

    assert evidence is not None
    assert evidence.verified_delivery is True
    assert evidence.staffed is True
    assert evidence.v6_delivery is False
    assert evidence.verification_reason == "host_encrypted_task_delivery"
    assert evidence.child_id == _ENC_CHILD
    assert evidence.binding_kind == "child_id"
    assert evidence.cards[0].specialist_slug == "code-reviewer"
    assert len(store.consumed) == 1
    assert store.consumed[0]["child_id"] == _ENC_CHILD


def test_host_encrypted_canary_evidence_refuses_ciphertext_mismatch(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    child, parent = _write_encrypted_rollouts(root)
    tampered = [
        (
            {
                **record,
                "payload": {
                    **record["payload"],
                    "arguments": json.dumps(
                        {
                            "agent_type": "Code Reviewer",
                            "fork_turns": "none",
                            "message": "gAAAAAB" + "z" * 300,
                            "task_name": "code_reviewer",
                        }
                    ),
                },
            }
            if record["payload"].get("type") == "function_call"
            else record
        )
        for record in _encrypted_parent_records()
    ]
    parent.write_text(
        "".join(json.dumps(record) + "\n" for record in tampered),
        encoding="utf-8",
    )
    store = _EncryptedDeliveryStore()

    evidence = subject._host_encrypted_canary_evidence(
        store,
        artifact=child,
        route=_encrypted_route(),
        child_id=_ENC_CHILD,
        parent_session_id=_ENC_PARENT,
        root=root,
    )

    assert evidence is None
    assert store.consumed == []


def test_host_encrypted_canary_evidence_replays_persisted_receipt_read_only(
    tmp_path: Path,
    codex_v1491_artifact_trust: None,
) -> None:
    root = tmp_path / "sessions"
    child, _parent = _write_encrypted_rollouts(root)
    store = _EncryptedDeliveryStore()
    first = subject._host_encrypted_canary_evidence(
        store,
        artifact=child,
        route=_encrypted_route(),
        child_id=_ENC_CHILD,
        parent_session_id=_ENC_PARENT,
        root=root,
    )
    assert first is not None and len(store.consumed) == 1
    store.receipt = {
        "verified_delivery": True,
        "nonce": "n" * 32,
        "artifact_digest": first.artifact_digest,
        "child_id": _ENC_CHILD,
        "binding_kind": "child_id",
        "binding_id": _ENC_CHILD,
    }

    replay = subject._host_encrypted_canary_evidence(
        store,
        artifact=child,
        route=_encrypted_route(),
        child_id=_ENC_CHILD,
        parent_session_id=_ENC_PARENT,
        root=root,
    )

    assert replay is not None and replay.verified_delivery is True
    assert len(store.consumed) == 1


def test_codex_host_encrypted_task_delivery_requires_one_envelope(
    tmp_path: Path,
) -> None:
    records = _encrypted_child_records()
    text = "".join(json.dumps(record) + "\n" for record in records)
    parsed = subject._codex_host_encrypted_task_delivery(text)
    assert parsed is not None and parsed[0] == _ENC_TOKEN

    duplicated = [*records[:3], records[2], *records[3:]]
    text = "".join(json.dumps(record) + "\n" for record in duplicated)
    assert subject._codex_host_encrypted_task_delivery(text) is None

    wrong_preamble = json.loads(json.dumps(records))
    wrong_preamble[2]["payload"]["content"][0]["text"] = "Message Type: OTHER"
    text = "".join(json.dumps(record) + "\n" for record in wrong_preamble)
    assert subject._codex_host_encrypted_task_delivery(text) is None
