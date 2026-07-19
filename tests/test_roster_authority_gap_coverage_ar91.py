"""Adversarial coverage for fail-closed roster activation authority."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

import pytest

from agency_runtime.core.roster import review as roster_review
from agency_runtime.core.roster import sync as roster_sync
from agency_runtime.core.roster.ingress import RosterSyncError
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.store import roster_authority as subject


class _Result:
    def __init__(self, row: Any = None, *, rows: list[Any] | None = None) -> None:
        self.row = row
        self.rows = [] if rows is None else rows

    def fetchone(self) -> Any:
        return self.row

    def fetchall(self) -> list[Any]:
        return self.rows


class _SequenceConnection:
    def __init__(self, results: list[_Result]) -> None:
        self.results = list(results)

    def execute(self, *_args: Any, **_kwargs: Any) -> _Result:
        return self.results.pop(0)


def _candidate_events(*, reason: str = "snapshot_id=snapshot") -> list[dict[str, Any]]:
    return [
        {
            "event_rowid": 1,
            "event_type": "approved",
            "from_status": "pending",
            "to_status": "approved",
            "reason": reason,
            "audit_id": "audit-approved",
            "created_at": "2026-07-18T00:00:00+00:00",
        },
        {
            "event_rowid": 2,
            "event_type": "activated",
            "from_status": "approved",
            "to_status": "activated",
            "reason": reason,
            "audit_id": "audit-activated",
            "created_at": "2026-07-18T00:00:01+00:00",
        },
    ]


def _snapshot_event_rows() -> list[dict[str, Any]]:
    return [
        {
            "import_event_sequence": 1,
            "event_type": "snapshot_approved",
            "agent_slug": "",
            "detail": "{}",
            "created_at": "2026-07-18T00:00:01+00:00",
        },
        {
            "import_event_sequence": 2,
            "event_type": "snapshot_activated",
            "agent_slug": "",
            "detail": "{}",
            "created_at": "2026-07-18T00:00:02+00:00",
        },
    ]


def test_scalar_timestamp_and_json_helpers_reject_malformed_values() -> None:
    with pytest.raises(ValueError, match="label is invalid"):
        subject._strict_text(1, label="label")
    with pytest.raises(ValueError, match="label is invalid"):
        subject._strict_text("\ud800", label="label")
    with pytest.raises(ValueError, match="timestamp is invalid"):
        subject._timestamp("not-a-timestamp")
    with pytest.raises(ValueError, match="timestamp is invalid"):
        subject._timestamp("2026-07-18T00:00:00")
    with pytest.raises(ValueError, match="list is invalid"):
        subject._strict_json_string_list("{", label="list")
    with pytest.raises(ValueError, match="event ordering"):
        subject._event_order(
            {"created_at": "2026-07-18T00:00:00+00:00", "rowid": 0},
            rowid_field="rowid",
        )


def test_candidate_authority_events_reject_ambiguous_type_and_snapshot_reason() -> None:
    duplicate = _candidate_events()
    duplicate[1]["event_type"] = "approved"
    with pytest.raises(ValueError, match="missing or ambiguous"):
        subject._authority_events(
            _SequenceConnection([_Result(rows=duplicate)]),
            candidate_id="candidate",
        )

    with pytest.raises(ValueError, match="snapshot binding"):
        subject._authority_events(
            _SequenceConnection([_Result(rows=_candidate_events(reason="not-bound"))]),
            candidate_id="candidate",
        )


def test_bound_audit_rejects_nontext_and_future_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="audit binding"):
        subject._assert_bound_audit(
            object(),
            event={"audit_id": 1},
            candidate_id="candidate",
            candidate_version="version",
            candidate_hash="a" * 64,
        )

    monkeypatch.setattr(
        roster_review,
        "assert_bound_candidate_audit_from_connection",
        lambda *_args, **_kwargs: (
            {"created_at": "2026-07-18T00:00:02+00:00"},
            True,
        ),
    )
    with pytest.raises(ValueError, match="audit binding"):
        subject._assert_bound_audit(
            object(),
            event={
                "audit_id": "audit",
                "created_at": "2026-07-18T00:00:01+00:00",
            },
            candidate_id="candidate",
            candidate_version="version",
            candidate_hash="a" * 64,
        )


def _snapshot_connection(rows: list[dict[str, Any]]) -> _SequenceConnection:
    return _SequenceConnection(
        [
            _Result(None),
            _Result(None),
            _Result(rows=rows),
        ]
    )


def test_snapshot_events_reject_ambiguous_invalid_and_mismatched_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = _snapshot_event_rows()
    duplicate[1]["event_type"] = "snapshot_approved"
    with pytest.raises(ValueError, match="missing or ambiguous"):
        subject._snapshot_events(
            _snapshot_connection(duplicate),
            snapshot_id="snapshot",
            manifest_json="{}",
            candidate_ids=["candidate"],
            candidate_id="candidate",
            approved_audit_id="audit-approved",
            activated_audit_id="audit-activated",
        )

    monkeypatch.setattr(
        subject,
        "validate_snapshot_authority_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RosterSyncError("invalid")),
    )
    with pytest.raises(ValueError, match="snapshot activation authority"):
        subject._snapshot_events(
            _snapshot_connection(_snapshot_event_rows()),
            snapshot_id="snapshot",
            manifest_json="{}",
            candidate_ids=["candidate"],
            candidate_id="candidate",
            approved_audit_id="audit-approved",
            activated_audit_id="audit-activated",
        )

    monkeypatch.setattr(
        subject,
        "validate_snapshot_authority_detail",
        lambda *_args, **_kwargs: {"candidate": "wrong-audit"},
    )
    with pytest.raises(ValueError, match="audit identities"):
        subject._snapshot_events(
            _snapshot_connection(_snapshot_event_rows()),
            snapshot_id="snapshot",
            manifest_json="{}",
            candidate_ids=["candidate"],
            candidate_id="candidate",
            approved_audit_id="audit-approved",
            activated_audit_id="audit-activated",
        )


def _candidate_and_revision() -> tuple[dict[str, Any], dict[str, Any]]:
    content = "Review carefully."
    digest = sha256(content.encode("utf-8")).hexdigest()
    candidate = {
        "id": "candidate",
        "slug": "reviewer",
        "name": "Reviewer",
        "division": "engineering",
        "description": "Reviews changes",
        "source": "test",
        "source_id": "source",
        "source_version": "1.0.0",
        "version": "sha256:" + ("b" * 64),
        "hash": digest,
        "content": content,
        "categories": ["review"],
        "capabilities": ["analysis"],
        "tool_affinity": ["git"],
        "prompt_path": "agents/reviewer.md",
    }
    revision = {
        "agent_slug": candidate["slug"],
        "version": candidate["version"],
        "source_version": candidate["source_version"],
        "source_id": candidate["source_id"],
        "hash": digest,
        "content": content,
        "metadata": serialized_revision_metadata(candidate),
    }
    return candidate, revision


def _candidate_authority_connection(
    *,
    candidate_rows: list[dict[str, Any]],
) -> _SequenceConnection:
    return _SequenceConnection(
        [
            _Result(rows=candidate_rows),
            _Result({"approved": 1, "activated": 1, "manifest": "{}"}),
        ]
    )


def _patch_candidate_authority_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    manifest: dict[str, Any],
    assert_records: Any = None,
    snapshot_events: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> None:
    monkeypatch.setattr(
        subject,
        "_authority_events",
        lambda *_args, **_kwargs: (
            {
                "audit_id": "audit-approved",
                "created_at": "2026-07-18T00:00:00+00:00",
            },
            {
                "audit_id": "audit-activated",
                "created_at": "2026-07-18T00:00:02+00:00",
            },
            "snapshot",
        ),
    )
    monkeypatch.setattr(subject, "_assert_bound_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        roster_sync,
        "_snapshot_from_connection",
        lambda *_args, **_kwargs: (manifest, True),
    )
    monkeypatch.setattr(
        roster_sync,
        "_assert_candidate_records",
        assert_records or (lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(
        subject,
        "_snapshot_events",
        lambda *_args, **_kwargs: (
            snapshot_events
            or (
                {"created_at": "2026-07-18T00:00:01+00:00"},
                {"created_at": "2026-07-18T00:00:03+00:00"},
            )
        ),
    )


def test_candidate_snapshot_authority_rejects_missing_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _candidate, revision = _candidate_and_revision()
    _patch_candidate_authority_dependencies(monkeypatch, manifest={})
    with pytest.raises(ValueError, match="missing or ambiguous"):
        subject._assert_candidate_snapshot_authority(
            _candidate_authority_connection(candidate_rows=[]),
            slug="reviewer",
            revision=revision,
            content=revision["content"],
        )


@pytest.mark.parametrize(
    "failure",
    ["inactive_manifest", "missing_match", "record_error", "mismatch", "event_order"],
)
def test_candidate_snapshot_authority_rejects_each_invalid_dependency(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    candidate, revision = _candidate_and_revision()
    manifest = {
        "approved": failure != "inactive_manifest",
        "candidates": [] if failure == "missing_match" else [candidate],
        "active_basis": ["reviewer"],
    }
    assert_records = (
        (lambda *_args, **_kwargs: (_ for _ in ()).throw(RosterSyncError("invalid")))
        if failure == "record_error"
        else None
    )
    if failure == "mismatch":
        candidate = {**candidate, "content": "different"}
        manifest["candidates"] = [candidate]
    snapshot_events = (
        (
            {"created_at": "2026-07-18T00:00:03+00:00"},
            {"created_at": "2026-07-18T00:00:04+00:00"},
        )
        if failure == "event_order"
        else None
    )
    _patch_candidate_authority_dependencies(
        monkeypatch,
        manifest=manifest,
        assert_records=assert_records,
        snapshot_events=snapshot_events,
    )
    expected = {
        "inactive_manifest": "snapshot activation authority",
        "missing_match": "candidate authority",
        "record_error": "candidate authority is invalid",
        "mismatch": "does not match",
        "event_order": "event order",
    }[failure]
    with pytest.raises(ValueError, match=expected):
        subject._assert_candidate_snapshot_authority(
            _candidate_authority_connection(candidate_rows=[{"id": "candidate"}]),
            slug="reviewer",
            revision=revision,
            content=revision["content"],
        )
