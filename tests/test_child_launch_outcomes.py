"""Contracts for resolving what happened to every harness-spawned child launch."""

from __future__ import annotations

import base64
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from agency_runtime.core.child_launch_outcomes import (
    DECLINED,
    STAFFED,
    UNRECORDED,
    original_assignment,
    read_child_launch,
    resolve_child_launch_outcomes,
)

_ASSIGNMENT = "Identify the regression risk of replacing return value with return value.strip()."


def _envelope(decision_id: str) -> str:
    payload = json.dumps({"decision_id": decision_id, "version": 6}).encode("utf-8")
    encoded = base64.b64encode(payload).decode("ascii")
    return f"\n\n[AGENCY INFERENCE TEAM v6]\n<!-- agency-native-child-team:v6:{encoded} -->"


def _write_child(
    root: Path,
    *,
    session: str,
    child_id: str,
    assignment: str,
    launch_id: str = "",
    envelope: str = "",
    launched_at: str = "2026-08-18T01:00:00.000Z",
) -> Path:
    subagents = root / session / "subagents"
    subagents.mkdir(parents=True, exist_ok=True)
    artifact = subagents / f"agent-{child_id}.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "type": "user",
                "isSidechain": True,
                "sessionId": session,
                "timestamp": launched_at,
                "message": {"role": "user", "content": assignment + envelope},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if launch_id:
        (subagents / f"agent-{child_id}.meta.json").write_text(
            json.dumps({"toolUseId": launch_id}), encoding="utf-8"
        )
    return artifact


def _resolver(
    root: Path,
    *,
    by_id: dict[str, Any] | None = None,
    by_hash: dict[tuple[str, str], Any] | None = None,
    by_fingerprint: dict[str, Any] | None = None,
    since: str = "",
) -> dict[str, Any]:
    return resolve_child_launch_outcomes(
        root,
        host="claude",
        decision_by_id=lambda value: (by_id or {}).get(value),
        decision_by_query_hash=lambda session, digest: (by_hash or {}).get((session, digest)),
        decision_by_fingerprint=lambda session, launch, digest: (by_fingerprint or {}).get(launch),
        since=since,
    )


def test_the_envelope_hash_is_taken_before_delivery_appended_it(tmp_path: Path) -> None:
    """The stored hash is of the pre-delivery text, so the envelope must come off.

    Hashing the delivered text instead would make every staffed child look
    unrecorded, which is the exact reading this module exists to prevent.
    """

    artifact = _write_child(
        tmp_path,
        session="session-a",
        child_id="child1",
        assignment=_ASSIGNMENT,
        envelope=_envelope("native-child-abc"),
    )
    launch = read_child_launch(artifact)
    assert launch is not None
    assert launch["assignment_sha256"] == sha256(_ASSIGNMENT.encode("utf-8")).hexdigest()
    assert launch["envelope_decision_id"] == "native-child-abc"
    assert original_assignment(_ASSIGNMENT) == _ASSIGNMENT


def test_each_join_key_resolves_a_launch_the_others_miss(tmp_path: Path) -> None:
    """The three keys are complementary; any one alone under-reports coverage.

    This is the measured shape from 2026-08-18, where the fingerprint resolved
    one declined child and the assignment hash resolved a different one.
    """

    _write_child(
        tmp_path,
        session="session-a",
        child_id="staffed",
        assignment=_ASSIGNMENT,
        launch_id="toolu_staffed",
        envelope=_envelope("native-child-staffed"),
    )
    _write_child(
        tmp_path,
        session="session-a",
        child_id="byhash",
        assignment="A different assignment entirely.",
        launch_id="toolu_byhash",
    )
    _write_child(
        tmp_path,
        session="session-a",
        child_id="byfingerprint",
        assignment="A third assignment.",
        launch_id="toolu_byfingerprint",
    )
    _write_child(
        tmp_path,
        session="session-a",
        child_id="silent",
        assignment="A fourth assignment nobody recorded.",
        launch_id="toolu_silent",
    )

    report = _resolver(
        tmp_path,
        by_id={"native-child-staffed": {"id": "d1", "status": "applied", "source": "nci"}},
        by_hash={
            (
                "session-a",
                sha256(b"A different assignment entirely.").hexdigest(),
            ): {"id": "d2", "status": "inference_invalid", "source": "ncif"}
        },
        by_fingerprint={
            "toolu_byfingerprint": {"id": "d3", "status": "inference_abstained", "source": "ncia"}
        },
    )

    outcomes = {item["child_id"]: item for item in report["launches"]}
    assert outcomes["staffed"]["outcome"] == STAFFED
    assert outcomes["staffed"]["matched_by"] == "envelope_decision_id"
    assert outcomes["byhash"]["outcome"] == DECLINED
    assert outcomes["byhash"]["matched_by"] == "assignment_query_hash"
    assert outcomes["byfingerprint"]["outcome"] == DECLINED
    assert outcomes["byfingerprint"]["matched_by"] == "context_fingerprint"
    assert outcomes["silent"]["outcome"] == UNRECORDED
    assert outcomes["silent"]["matched_by"] == ""
    assert report["counts"] == {STAFFED: 1, DECLINED: 2, UNRECORDED: 1}
    assert report["recorded_rate"] == 0.75


def test_a_launch_resolves_without_a_launch_id_or_an_envelope(tmp_path: Path) -> None:
    """A child with no meta file still resolves by its own assignment hash."""

    _write_child(
        tmp_path,
        session="session-b",
        child_id="nometa",
        assignment=_ASSIGNMENT,
    )
    report = _resolver(
        tmp_path,
        by_hash={
            (
                "session-b",
                sha256(_ASSIGNMENT.encode("utf-8")).hexdigest(),
            ): {"id": "d9", "status": "applied", "source": "nci"}
        },
    )
    assert report["counts"][STAFFED] == 1
    assert report["launches"][0]["launch_id"] == ""


def test_an_unreadable_artifact_is_counted_rather_than_skipped(tmp_path: Path) -> None:
    """A dropped artifact would recreate the silence this module reports on."""

    subagents = tmp_path / "session-c" / "subagents"
    subagents.mkdir(parents=True)
    (subagents / "agent-broken.jsonl").write_text("{not json", encoding="utf-8")
    report = _resolver(tmp_path)
    assert report["artifacts_unreadable"] == 1
    assert report["launches_seen"] == 0
    assert report["recorded_rate"] is None


def test_an_absent_root_reports_itself_rather_than_an_empty_success(tmp_path: Path) -> None:
    report = _resolver(tmp_path / "missing")
    assert report["root_present"] is False
    assert report["counts"] == {STAFFED: 0, DECLINED: 0, UNRECORDED: 0}


def test_launches_before_the_window_are_reported_not_silently_dropped(tmp_path: Path) -> None:
    """An artifact root holds children from every runtime that ever ran here.

    Counting all of them against today's install reports a rate for a runtime
    that never saw them, so the window is explicit and what it excluded is
    stated rather than quietly missing from the denominator.
    """

    _write_child(
        tmp_path,
        session="session-d",
        child_id="ancient",
        assignment="Work from a previous runtime.",
        launched_at="2026-07-01T00:00:00.000Z",
    )
    _write_child(
        tmp_path,
        session="session-d",
        child_id="current",
        assignment=_ASSIGNMENT,
        launched_at="2026-08-18T02:00:00.000Z",
    )

    report = _resolver(
        tmp_path,
        by_hash={
            (
                "session-d",
                sha256(_ASSIGNMENT.encode("utf-8")).hexdigest(),
            ): {"id": "d1", "status": "applied", "source": "nci"}
        },
        since="2026-08-18T00:00:00.000Z",
    )

    assert report["launches_out_of_window"] == 1
    assert report["launches_seen"] == 1
    assert report["counts"][STAFFED] == 1
    assert report["recorded_rate"] == 1.0
    assert report["since"] == "2026-08-18T00:00:00.000Z"


def test_an_assignment_that_merely_mentions_the_marker_is_not_truncated(tmp_path: Path) -> None:
    """Quoting a delivery marker is not a delivery.

    A review assignment that discusses envelopes contains these markers as
    prose. Cutting on the mention truncates the assignment, and the short hash
    then matches nothing -- reporting a child that has a receipt as unrecorded.
    That is exactly how this shipped on 2026-08-18.
    """

    discusses = (
        "READ-ONLY review. Check whether record zero carries an "
        "[AGENCY INFERENCE TEAM v6] envelope and whether "
        "<!-- agency-native-child-team:v6: is present. Report findings only."
    )
    assert original_assignment(discusses) == discusses

    _write_child(tmp_path, session="session-e", child_id="mentions", assignment=discusses)
    report = _resolver(
        tmp_path,
        by_hash={
            (
                "session-e",
                sha256(discusses.encode("utf-8")).hexdigest(),
            ): {"id": "d7", "status": "inference_invalid", "source": "ncif"}
        },
    )
    assert report["counts"][DECLINED] == 1
    assert report["launches"][0]["matched_by"] == "assignment_query_hash"


def test_a_shortened_child_copy_still_resolves_through_the_parent_transcript(
    tmp_path: Path,
) -> None:
    """The child artifact is not a faithful copy of the assignment.

    Measured 2026-08-18: a 3,184-character launch input appears in the child's
    record zero as 867 characters. Agency hashed what the parent recorded, so
    an artifact-only resolver reports every shortened launch as unrecorded no
    matter how carefully it strips.
    """

    full = "Review this. " + ("detail " * 500)
    project = tmp_path
    _write_child(
        project,
        session="session-f",
        child_id="shortened",
        assignment="Review this. detail detail",  # the host's shortened copy
        launch_id="toolu_shortened",
    )
    (project / "session-f.jsonl").write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_shortened",
                            "input": {"prompt": full},
                        }
                    ]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = _resolver(
        project,
        by_hash={
            (
                "session-f",
                sha256(full.encode("utf-8")).hexdigest(),
            ): {"id": "d8", "status": "inference_invalid", "source": "ncif"}
        },
    )
    assert report["counts"][DECLINED] == 1
    assert report["launches"][0]["matched_by"] == "assignment_query_hash"
