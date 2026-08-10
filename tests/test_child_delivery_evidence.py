"""Rule 4, independently verified: read the host's own artifact for the card.

These tests exist because ``specialists_loaded`` is written by the code under
test. Everything here reads a transcript the *host* wrote and asks whether the
card actually arrived — and, just as importantly, refuses to count a marker the
child merely read back later.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.core import child_delivery_evidence as subject
from agency_runtime.core.child_delivery_evidence import (
    MAX_LAUNCH_PREFIX_BYTES,
    child_delivery_evidence,
    claude_child_delivery_evidence,
    codex_child_delivery_evidence,
    scan_child_delivery_evidence,
)
from agency_runtime.core.native_child_prompt_delivery import render_jit_specialist_delivery
from agency_runtime.core.roster.revisions import content_digest

PARENT_SESSION = "37a4776a-92f4-4fe8-b2fe-926652d70225"
CHILD_AGENT = "a19cc709eae42e6aa"
PROMPT = "You are a SQLite specialist. Prefer WAL mode and bounded transactions."
OTHER_PROMPT = "You are a security reviewer. Name the exact attacker capability."


@pytest.fixture
def private_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat the fixture root as ACL-private, the way a real host directory is.

    Windows ``Temp`` is not private, so a synthetic artifact can never satisfy
    the real gate. ``test_a_directory_other_accounts_can_write_is_refused``
    leaves the gate alone and proves it still bites.
    """

    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)


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
) -> dict[str, object]:
    return {
        "parentUuid": None,
        "isSidechain": sidechain,
        "agentId": CHILD_AGENT,
        "type": record_type,
        "message": {"role": "user", "content": text},
        "sessionId": PARENT_SESSION,
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
    payload: dict[str, object] = {"id": "019fbb8b-1394-7413"}
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
        tmp_path / "2026" / "08" / "01" / "rollout-2026-08-01T00-18-01-019fbb8b.jsonl",
        records,
    )


def test_a_launch_record_proves_the_child_received_the_card(
    tmp_path: Path,
    private_root: None,
) -> None:
    artifact = _claude_artifact(tmp_path, [_claude_record(_envelope("Audit the schema."))])

    evidence = claude_child_delivery_evidence(artifact)

    assert evidence is not None
    assert evidence.staffed is True
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
    assert evidence.staffed is True
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
    assert evidence.staffed is True


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
    assert evidence.staffed is True


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
    assert all(finding.staffed for finding in findings)


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
