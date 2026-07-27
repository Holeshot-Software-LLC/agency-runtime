from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.roster import sync as subject
from agency_runtime.core.roster.ingress import ManifestImportOutcome, RosterSyncError
from agency_runtime.core.roster.remediation import RosterRemediationError
from agency_runtime.core.store.sqlite import Store


class _Rows:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []

    def fetchone(self) -> Any:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[Any]:
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class _QueueConnection:
    def __init__(self, *results: list[Any]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, Any]] = []

    def execute(self, sql: str, parameters: Any = ()) -> _Rows:
        self.calls.append((sql, parameters))
        return _Rows(self.results.pop(0) if self.results else [])


class _TransactionConnection(_QueueConnection):
    def __init__(self, *results: list[Any]) -> None:
        super().__init__(*results)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def executemany(self, sql: str, parameters: Any) -> _Rows:
        self.calls.append((sql, list(parameters)))
        return _Rows()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _RouterConnection(_TransactionConnection):
    def __init__(self, router: Any) -> None:
        super().__init__()
        self.router = router

    def execute(self, sql: str, parameters: Any = ()) -> _Rows:
        self.calls.append((sql, parameters))
        return _Rows(self.router(sql, parameters))


def _valid_authority_dependencies() -> list[dict[str, str]]:
    kinds = (
        "candidate",
        "candidate_audit",
        "candidate_download",
        "queue_event",
        "queue_download",
        "queue_source_scan",
        "resolution_event",
        "source",
        "candidate_source_scan",
    )
    return [
        {"kind": kind, "id": f"{kind}-id", "hash": f"{index:064x}"}
        for index, kind in enumerate(kinds, start=1)
    ]


def _scan_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "scan",
        "source_id": "source",
        "status": "partial",
        "manifest_hash": subject._source_scan_manifest_hash([]),
        "entry_count": 0,
        "candidate_count": 0,
        "quarantined_count": 0,
        "ignored_count": 0,
        "created_at": "2026-07-18T12:00:00+00:00",
        "source_enabled": 1,
    }
    row.update(overrides)
    return row


def _header_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "event_order": 2,
        "id": "header",
        "agent_slug": "",
        "detail": "{}",
        "created_at": "2026-07-18T12:00:00+00:00",
    }
    row.update(overrides)
    return row


def _unknown_manifest(root: Path) -> Any:
    source = root / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "unknown-encoding.md").write_text(
        "---\nname: Unknown Encoding\ndescription: Quarantine me.\n---\n"
        "## Broken\x07 heading\nNo repair may be guessed.\n",
        encoding="utf-8",
    )
    return subject.download_from_source(str(source))


@pytest.mark.parametrize("value", ["not-a-time", "2026-07-18T12:00:00"])
def test_event_timestamp_rejects_invalid_or_naive_values(value: str) -> None:
    with pytest.raises(RosterSyncError, match="event time is invalid"):
        subject._event_timestamp(value, "event time")


def test_remediation_schema_and_event_bounds_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject, "agent_import_event_sequence_schema_is_current", lambda _conn: False
    )
    with pytest.raises(RosterSyncError, match="authority schema is invalid"):
        subject._assert_remediation_authority_available(object())

    subject._assert_bounded_import_event_types(object(), ())
    conn = _QueueConnection([{"id": "oversized"}])
    with pytest.raises(RosterSyncError, match="detail exceeds"):
        subject._assert_bounded_import_event_types(conn, ("queued",))


@pytest.mark.parametrize("detail", [None, b"bytes"])
def test_bounded_event_detail_requires_bounded_text(detail: Any) -> None:
    with pytest.raises(RosterSyncError, match="integrity bound"):
        subject._bounded_event_detail({"detail": detail}, "event")


def test_bounded_event_detail_rejects_oversize_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_REMEDIATION_EVENT_BYTES", 1)
    with pytest.raises(RosterSyncError, match="integrity bound"):
        subject._bounded_event_detail({"detail": "xx"}, "event")


@pytest.mark.parametrize("value", [None, 1])
def test_stored_receipt_text_rejects_non_text(value: Any) -> None:
    with pytest.raises(RosterSyncError, match="must be text"):
        subject._stored_receipt_text(value, 10, "receipt")


def test_stored_receipt_text_rejects_empty_text() -> None:
    with pytest.raises(RosterSyncError, match="must not be empty"):
        subject._stored_receipt_text("", 10, "receipt")
    assert subject._stored_receipt_text("", 10, "receipt", allow_empty=True) == ""


def test_bounded_evidence_hash_rejects_noncanonical_and_oversize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RosterSyncError, match="not canonical evidence"):
        subject._bounded_evidence_hash({"bad": object()}, "evidence")

    monkeypatch.setattr(subject, "MAX_TOTAL_SOURCE_BYTES", 1)
    with pytest.raises(RosterSyncError, match="integrity bound"):
        subject._bounded_evidence_hash({"a": 1}, "evidence")


def test_canonical_authority_receipt_rejects_conflicts_and_bad_closures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = [
        {"kind": "candidate", "id": "same", "hash": "1" * 64},
        {"kind": "candidate", "id": "same", "hash": "2" * 64},
    ]
    with pytest.raises(RosterSyncError, match="conflicting dependencies"):
        subject._canonical_authority_receipt(duplicate)
    with pytest.raises(RosterSyncError, match="dependency closure is invalid"):
        subject._canonical_authority_receipt([])

    dependencies = _valid_authority_dependencies()

    def invalid_receipt(_dependencies: Any) -> str:
        raise ValueError("invalid")

    monkeypatch.setattr(subject, "canonical_remediation_authority_receipt", invalid_receipt)
    with pytest.raises(RosterSyncError, match="dependency closure is invalid"):
        subject._canonical_authority_receipt(dependencies)


def test_canonical_authority_receipt_rejects_oversize_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "MAX_REMEDIATION_EVENT_BYTES", 1)
    with pytest.raises(RosterSyncError, match="evidence receipt exceeds"):
        subject._canonical_authority_receipt(_valid_authority_dependencies())


def test_manifest_batch_rejects_duplicate_relative_paths() -> None:
    outcome = ManifestImportOutcome(
        status="ignored",
        origin="source/one.md",
        relative_path="one.md",
        slug="",
        content_hash="1" * 64,
        finding="ignored",
    )
    with pytest.raises(RosterSyncError, match="duplicate relative path"):
        subject._validated_manifest_batch([], [outcome, outcome])


def test_scan_provenance_timestamp_and_order_validation() -> None:
    valid_time = "2026-07-18T12:00:00+00:00"
    invalid_orders: list[Any] = [True, "1", 0, 2]
    for event_order in invalid_orders:
        with pytest.raises(RosterSyncError, match="does not precede"):
            subject._assert_scan_provenance_precedes_header(
                event_order=event_order,
                event_created_at=valid_time,
                header_order=2,
                scan_created_at=valid_time,
                label="provenance",
            )
    with pytest.raises(RosterSyncError, match="does not precede"):
        subject._assert_scan_provenance_precedes_header(
            event_order=1,
            event_created_at="2026-07-18T12:00:01+00:00",
            header_order=2,
            scan_created_at=valid_time,
            label="provenance",
        )


@pytest.mark.parametrize(
    ("scan", "message"),
    [
        (
            {
                "entry_count": True,
                "candidate_count": 0,
                "quarantined_count": 0,
                "ignored_count": 0,
                "status": "partial",
            },
            "counts are invalid",
        ),
        (
            {
                "entry_count": 1,
                "candidate_count": 0,
                "quarantined_count": 0,
                "ignored_count": 0,
                "status": "complete",
            },
            "counts are invalid",
        ),
        (
            {
                "entry_count": 0,
                "candidate_count": 0,
                "quarantined_count": 0,
                "ignored_count": 0,
                "status": "complete",
            },
            "counts are invalid",
        ),
    ],
)
def test_source_scan_declaration_rejects_invalid_counts(
    scan: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(RosterSyncError, match=message):
        subject._validated_source_scan_declaration(scan, scan_id="scan")


def test_source_scan_structural_evidence_rejects_invalid_event_order() -> None:
    with pytest.raises(RosterSyncError, match="header order is invalid"):
        subject._source_scan_structural_evidence(
            {},
            {"event_order": True},
            scan_id="scan",
        )


@pytest.mark.parametrize("limit", [True, 0, 1001])
def test_source_scan_list_limit_is_strict(limit: Any) -> None:
    with pytest.raises(ValueError, match="between 1 and 1000"):
        subject.list_source_scans(object(), limit=limit)


def test_cached_scan_helpers_cover_uncached_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_validated_source_scan_entry",
        lambda _conn, scan_id, relative_path: {
            "id": scan_id,
            "relative_path": relative_path,
        },
    )
    monkeypatch.setattr(
        subject,
        "_validated_source_scan",
        lambda _conn, scan_id, **_kwargs: {"id": scan_id},
    )
    assert subject._cached_remediation_source_scan(
        object(),
        "scan",
        "agent.md",
        None,
    ) == {"id": "scan", "relative_path": "agent.md"}
    assert subject._cached_full_remediation_source_scan(
        object(),
        "scan",
        None,
    ) == {"id": "scan"}


def test_full_scan_entry_comparison_rejects_missing_or_changed_commitment() -> None:
    local_scan = {
        "_structural_evidence": {"header": "local"},
        "_structural_hash": "1" * 64,
        "_selected_entry_evidence": {"entry": "local"},
        "_selected_entry_hash": "2" * 64,
    }
    full_scan = {
        "entries": [],
        "_entry_authority_evidence": {},
        "_structural_evidence": {"header": "local"},
        "_structural_hash": "1" * 64,
    }
    with pytest.raises(RosterSyncError, match="entry is unavailable"):
        subject._assert_local_scan_entry_matches_full_scan(
            local_scan,
            full_scan,
            scan_id="scan",
            relative_path="agent.md",
        )

    full_scan["entries"] = [{"relative_path": "agent.md"}]
    full_scan["_entry_authority_evidence"] = {"agent.md": {"entry": "different"}}
    with pytest.raises(RosterSyncError, match="commitment changed"):
        subject._assert_local_scan_entry_matches_full_scan(
            local_scan,
            full_scan,
            scan_id="scan",
            relative_path="agent.md",
        )


@pytest.mark.parametrize(
    ("function", "arguments"),
    [
        (subject._authorized_resolution_integrity_sql, ("bad", "resolution", "queued")),
        (subject._authorized_resolution_exists_sql, ("bad",)),
    ],
)
def test_remediation_sql_builders_reject_unknown_aliases(
    function: Any,
    arguments: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="unsupported remediation"):
        function(*arguments)


def test_resolution_cursor_uses_authority_query() -> None:
    conn = _QueueConnection([{"event_order": 7}])
    assert (
        subject._remediation_cursor_order(
            conn,
            "resolution-id",
            event_type="manifest_entry_remediation_resolved",
            label="cursor",
        )
        == 7
    )
    assert "agent_remediation_resolution_authority" in conn.calls[0][0]


def test_projected_contract_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "contract_for_projected_candidate", lambda *_args: None)
    original = {"slug": "custom", "hash": "1" * 64}
    assert subject._with_projected_contract(original) == original

    monkeypatch.setattr(
        subject,
        "contract_for_projected_candidate",
        lambda *_args: {
            "source_content_hash": "2" * 64,
            "relative_path": "agent.md",
        },
    )

    def invalid_contract(*_args: Any, **_kwargs: Any) -> None:
        raise RosterRemediationError("invalid")

    monkeypatch.setattr(subject, "verify_projected_candidate_contract", invalid_contract)
    with pytest.raises(RosterSyncError, match="projected candidate metadata is invalid"):
        subject._with_projected_contract(original)


def test_active_agent_fingerprint_requires_slug() -> None:
    with pytest.raises(RosterSyncError, match="requires a slug"):
        subject._active_agent_fingerprint({})


def test_persist_snapshot_manifest_requires_candidate_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "project_snapshot_summary", lambda _manifest: {})
    with pytest.raises(RosterSyncError, match="candidates must be a list"):
        subject._persist_snapshot_manifest(
            object(),
            {
                "snapshot_id": "snapshot",
                "created_at": "now",
                "candidates": None,
            },
        )


def test_retirement_diff_rejects_empty_duplicate_and_oversize_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RosterSyncError, match="at least one"):
        subject.create_retirement_diff(object(), scan_id="scan", slugs=[])
    with pytest.raises(RosterSyncError, match="must be unique"):
        subject.create_retirement_diff(object(), scan_id="scan", slugs=["a", "a"])
    monkeypatch.setattr(subject, "MAX_SOURCE_CANDIDATES", 1)
    with pytest.raises(RosterSyncError, match="too many"):
        subject.create_retirement_diff(object(), scan_id="scan", slugs=["a", "b"])


def test_snapshot_manifest_lists_rejects_retirement_shape_and_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = {
        "snapshot_id": "snapshot",
        "approved": False,
        "candidates": [],
        "candidate_ids": [],
    }
    with pytest.raises(RosterSyncError, match="retirement manifest is invalid"):
        subject._snapshot_manifest_lists(
            {**base, "retirements": {}},
            snapshot_id="snapshot",
            agent_count=0,
        )
    monkeypatch.setattr(subject, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(RosterSyncError, match="too many retirements"):
        subject._snapshot_manifest_lists(
            {**base, "retirements": [{}]},
            snapshot_id="snapshot",
            agent_count=0,
        )


def test_manifest_retirement_validation_failures() -> None:
    with pytest.raises(RosterSyncError, match="invalid retirement"):
        subject._validated_manifest_retirements([object()], snapshot_id="snapshot")

    invalid = {
        "hash": "bad",
        "scan_id": "scan",
        "slug": "agent",
        "source_id": "source",
        "version": "v1",
    }
    with pytest.raises(RosterSyncError, match="retirement identity is invalid"):
        subject._validated_manifest_retirements([invalid], snapshot_id="snapshot")

    valid = {**invalid, "hash": "1" * 64}
    with pytest.raises(RosterSyncError, match="duplicate retirements"):
        subject._validated_manifest_retirements([valid, valid], snapshot_id="snapshot")


def test_manifest_active_basis_rejects_bad_fingerprint_and_delta() -> None:
    with pytest.raises(RosterSyncError, match="active basis is invalid"):
        subject._validate_manifest_active_basis(
            {"active_basis": {"agent": "bad"}},
            "snapshot",
        )
    with pytest.raises(RosterSyncError, match="does not match its delta"):
        subject._validate_manifest_active_basis(
            {"active_basis": {}},
            "snapshot",
            touched_slugs={"agent"},
        )


def test_snapshot_manifest_rejects_activate_retire_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {
        "snapshot_id": "snapshot",
        "approved": False,
        "active_basis": {"agent": None},
        "candidate_ids": ["candidate"],
        "candidates": [{}],
        "retirements": [{}],
    }
    monkeypatch.setattr(
        subject,
        "_snapshot_manifest_lists",
        lambda *_args, **_kwargs: (manifest, [{}], ["candidate"], [{}]),
    )
    monkeypatch.setattr(
        subject,
        "_validated_manifest_candidates",
        lambda *_args, **_kwargs: ([{"slug": "agent"}], ["candidate"]),
    )
    monkeypatch.setattr(subject, "_validate_manifest_candidate_identity", lambda *_a, **_k: None)
    monkeypatch.setattr(
        subject,
        "_validated_manifest_retirements",
        lambda *_args, **_kwargs: [{"slug": "agent"}],
    )
    with pytest.raises(RosterSyncError, match="both activates and retires"):
        subject._validated_snapshot_manifest(
            manifest,
            snapshot_id="snapshot",
            agent_count=1,
        )


def test_preflight_rejects_registered_intermediate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "is_registered_encoding_intermediate", lambda _content: True)
    with pytest.raises(RosterSyncError, match="unprojected registered encoding"):
        subject._preflight_candidate_versions(
            object(),
            [{"slug": "agent", "version": "v1", "content": "encoded"}],
        )


def test_candidate_origin_wraps_lookup_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_candidate(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyError("missing")

    monkeypatch.setattr(subject, "candidate_record_from_connection", missing_candidate)
    with pytest.raises(RosterSyncError, match="candidate provenance is invalid"):
        subject._candidate_scan_origin(
            object(),
            {"source_id": "source"},
            {"candidate_id": "candidate", "slug": "agent"},
            scan_id="scan",
            relative_path="agent.md",
            content_hash="1" * 64,
            header_order=2,
            scan_created_at="2026-07-18T12:00:00+00:00",
        )


def test_resolution_provenance_wraps_missing_or_invalid_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"id": "candidate"}
    row = {"created_at": "2026-07-18T12:00:00+00:00", "event_order": 3}
    queue = {"created_at": "2026-07-18T12:00:00+00:00", "_event_order": 1}
    detail: dict[str, Any] = {}

    def invalid_evidence(*_args: Any, **_kwargs: Any) -> Any:
        raise RosterSyncError("invalid")

    monkeypatch.setattr(subject, "candidate_remediation_evidence_from_connection", invalid_evidence)
    with pytest.raises(RosterSyncError, match="transformation evidence is invalid"):
        subject._validate_remediated_resolution_provenance(
            object(),
            row,
            detail,
            queue,
            candidate,
        )

    monkeypatch.setattr(
        subject,
        "candidate_remediation_evidence_from_connection",
        lambda *_args: None,
    )
    with pytest.raises(RosterSyncError, match="transformation evidence is invalid"):
        subject._validate_remediated_resolution_provenance(
            object(),
            row,
            detail,
            queue,
            candidate,
        )


def test_resolution_detail_rejects_shape_hash_revision_and_disposition() -> None:
    valid = {
        "audit_id": "audit",
        "audit_revision": "sha256:" + "1" * 64,
        "candidate_download_id": "candidate-download",
        "candidate_hash": "2" * 64,
        "candidate_id": "candidate",
        "download_id": "download",
        "original_hash": "3" * 64,
        "origin": "agent.md",
        "policy_hash": "4" * 64,
        "queue_event_id": "queue",
        "relative_path": "agent.md",
        "resolution": "remediated_candidate",
        "scan_id": "scan",
        "source_hash": "5" * 64,
        "source_id": "source",
    }
    with pytest.raises(RosterSyncError, match="event fields are invalid"):
        subject._validated_remediation_resolution_detail({}, {})
    with pytest.raises(RosterSyncError, match="candidate_hash is invalid"):
        subject._validated_remediation_resolution_detail(
            {},
            {**valid, "candidate_hash": "bad"},
        )
    with pytest.raises(RosterSyncError, match="audit_revision is invalid"):
        subject._validated_remediation_resolution_detail(
            {},
            {**valid, "audit_revision": "bad"},
        )
    with pytest.raises(RosterSyncError, match="type is invalid"):
        subject._validated_remediation_resolution_detail(
            {},
            {**valid, "resolution": "bad"},
        )


def test_bounded_event_type_check_accepts_bounded_rows() -> None:
    subject._assert_bounded_import_event_types(_QueueConnection([]), ("queued",))


def test_manifest_persistence_detects_partial_quarantine_evidence(tmp_path: Path) -> None:
    outcome = _unknown_manifest(tmp_path).outcomes[0]
    conn = _QueueConnection([{"id": "download"}], [], [])
    with pytest.raises(RosterSyncError, match="quarantine evidence is incomplete"):
        subject._persist_rejected_manifest_entry(
            conn,
            object(),
            "source",
            outcome,
            scan_id="scan",
            now="2026-07-18T12:00:00+00:00",
        )


def test_manifest_persistence_detects_event_without_remediation_source() -> None:
    outcome = ManifestImportOutcome(
        status="candidate",
        origin="agent.md",
        relative_path="agent.md",
        slug="agent",
        content_hash="1" * 64,
        finding="repaired",
        source_content="original",
        remediation=SimpleNamespace(public_dict=lambda: {"schema": "test"}),
    )
    conn = _QueueConnection([], [{"id": "event"}])
    with pytest.raises(RosterSyncError, match="remediation evidence is incomplete"):
        subject._persist_remediated_manifest_source(
            conn,
            object(),
            "source",
            outcome,
            candidate_id="candidate",
            candidate_download_id="candidate-download",
            candidate_is_new=True,
            now="2026-07-18T12:00:00+00:00",
        )


def _candidate_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "id": "candidate",
        "source_id": "source",
        "slug": "agent",
        "hash": "1" * 64,
        "prompt_path": "agent.md",
        "content": "content",
        "download_hash": "1" * 64,
        "download_id": "download",
    }
    record.update(overrides)
    return record


@pytest.mark.parametrize(
    "candidate",
    [
        _candidate_record(source_id="other"),
        _candidate_record(slug="other"),
    ],
)
def test_candidate_origin_rejects_source_or_slug_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    candidate: dict[str, Any],
) -> None:
    monkeypatch.setattr(subject, "candidate_record_from_connection", lambda *_args: candidate)
    with pytest.raises(RosterSyncError, match="candidate provenance is invalid"):
        subject._candidate_scan_origin(
            object(),
            {"source_id": "source"},
            {"candidate_id": "candidate", "slug": "agent"},
            scan_id="scan",
            relative_path="agent.md",
            content_hash="1" * 64,
            header_order=2,
            scan_created_at="2026-07-18T12:00:00+00:00",
        )


def test_candidate_origin_rejects_missing_transformation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "candidate_record_from_connection",
        lambda *_args: _candidate_record(hash="2" * 64),
    )
    monkeypatch.setattr(
        subject,
        "candidate_remediation_evidence_from_connection",
        lambda *_args: None,
    )
    with pytest.raises(RosterSyncError, match="candidate provenance is invalid"):
        subject._candidate_scan_origin(
            object(),
            {"source_id": "source"},
            {"candidate_id": "candidate", "slug": "agent"},
            scan_id="scan",
            relative_path="agent.md",
            content_hash="1" * 64,
            header_order=2,
            scan_created_at="2026-07-18T12:00:00+00:00",
        )


def test_candidate_origin_rejects_empty_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "candidate_record_from_connection",
        lambda *_args: _candidate_record(prompt_path=""),
    )
    with pytest.raises(RosterSyncError, match="candidate origin must not be empty"):
        subject._candidate_scan_origin(
            object(),
            {"source_id": "source"},
            {"candidate_id": "candidate", "slug": "agent"},
            scan_id="scan",
            relative_path="agent.md",
            content_hash="1" * 64,
            header_order=2,
            scan_created_at="2026-07-18T12:00:00+00:00",
        )


def test_quarantined_origin_rejects_missing_or_mismatched_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = {
        "scan_id": "scan",
        "relative_path": "agent.md",
        "content_hash": "1" * 64,
        "header_order": 2,
        "scan_created_at": "2026-07-18T12:00:00+00:00",
    }
    with pytest.raises(RosterSyncError, match="quarantine provenance is invalid"):
        subject._quarantined_scan_origin(
            _QueueConnection([]),
            {"source_id": "source"},
            {"slug": "agent"},
            **arguments,
        )

    monkeypatch.setattr(
        subject,
        "_validated_remediation_queue_item_base",
        lambda *_args: {
            "source_id": "other",
            "slug": "agent",
            "relative_path": "agent.md",
            "receipt": {"original_hash": "1" * 64},
        },
    )
    with pytest.raises(RosterSyncError, match="quarantine provenance is invalid"):
        subject._quarantined_scan_origin(
            _QueueConnection([{"id": "queue"}]),
            {"source_id": "source"},
            {"slug": "agent"},
            **arguments,
        )


def test_ignored_origin_rejects_missing_shape_and_binding() -> None:
    arguments = {
        "scan_id": "scan",
        "relative_path": "agent.md",
        "content_hash": "1" * 64,
        "header_order": 2,
        "scan_created_at": "2026-07-18T12:00:00+00:00",
    }
    scan = {
        "source_id": "source",
        "created_at": "2026-07-18T12:00:00+00:00",
    }
    with pytest.raises(RosterSyncError, match="ignored provenance is invalid"):
        subject._ignored_scan_origin(_QueueConnection([]), scan, **arguments)

    invalid_shape = {"detail": "[]"}
    with pytest.raises(RosterSyncError, match="ignored provenance is invalid"):
        subject._ignored_scan_origin(_QueueConnection([invalid_shape]), scan, **arguments)

    detail = {
        "finding": "ignored",
        "hash": "1" * 64,
        "origin": "agent.md",
        "relative_path": "agent.md",
        "scan_id": "scan",
        "source_id": "source",
    }
    invalid_binding = {
        "event_order": 1,
        "id": "ignored",
        "agent_slug": "unexpected",
        "detail": json.dumps(detail),
        "created_at": scan["created_at"],
    }
    with pytest.raises(RosterSyncError, match="ignored provenance is invalid"):
        subject._ignored_scan_origin(_QueueConnection([invalid_binding]), scan, **arguments)


def test_source_scan_header_rejects_missing_and_bad_shape() -> None:
    scan = _scan_row()
    with pytest.raises(RosterSyncError, match="receipt header is invalid"):
        subject._validated_source_scan_header(
            _QueueConnection([]),
            scan,
            scan_id="scan",
            expected_status="partial",
        )
    with pytest.raises(RosterSyncError, match="receipt header is invalid"):
        subject._validated_source_scan_header(
            _QueueConnection([{"detail": "[]"}]),
            scan,
            scan_id="scan",
            expected_status="partial",
        )


def test_full_source_scan_rejects_missing_identity_and_header_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RosterSyncError, match="source scan not found"):
        subject._validated_source_scan(
            _QueueConnection([]),
            "scan",
            require_latest=False,
        )

    with pytest.raises(RosterSyncError, match="identity is invalid"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row(id="other")]),
            "scan",
            require_latest=False,
        )

    monkeypatch.setattr(
        subject,
        "_validated_source_scan_header",
        lambda *_args, **_kwargs: _header_row(event_order=True),
    )
    with pytest.raises(RosterSyncError, match="header order is invalid"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row()]),
            "scan",
            require_latest=False,
        )


def test_full_source_scan_rejects_entry_count_shape_and_source_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_validated_source_scan_header",
        lambda *_args, **_kwargs: _header_row(),
    )
    monkeypatch.setattr(
        subject,
        "_validated_source_scan_declaration",
        lambda *_args, **_kwargs: (
            {
                "entry_count": 0,
                "candidate_count": 0,
                "quarantined_count": 0,
                "ignored_count": 0,
            },
            "partial",
        ),
    )
    monkeypatch.setattr(subject, "MAX_SOURCE_FILES", 0)
    with pytest.raises(RosterSyncError, match="too many entries"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row()], [{"relative_path": "one"}]),
            "scan",
            require_latest=False,
        )

    monkeypatch.setattr(subject, "MAX_SOURCE_FILES", 2_000)
    invalid_entry = {
        "relative_path": "agent.md",
        "slug": "agent",
        "content_hash": "1" * 64,
        "status": "invalid",
        "candidate_id": None,
    }
    with pytest.raises(RosterSyncError, match="entry evidence is invalid"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row()], [invalid_entry]),
            "scan",
            require_latest=False,
        )

    monkeypatch.setattr(
        subject,
        "_source_scan_entry_origin",
        lambda *_args, **_kwargs: ("agent.md", "2" * 64, []),
    )
    ignored_entry = {
        "relative_path": "agent.md",
        "slug": "",
        "content_hash": "1" * 64,
        "status": "ignored",
        "candidate_id": None,
    }
    with pytest.raises(RosterSyncError, match="counts do not match"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row()], [ignored_entry]),
            "scan",
            require_latest=False,
        )

    with pytest.raises(RosterSyncError, match="disabled source"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row(source_enabled=0)], []),
            "scan",
            require_latest=False,
        )


def test_full_source_scan_rejects_stale_latest_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_validated_source_scan_header",
        lambda *_args, **_kwargs: _header_row(),
    )
    with pytest.raises(RosterSyncError, match="no longer the latest"):
        subject._validated_source_scan(
            _QueueConnection([_scan_row()], [], [{"id": "newer"}]),
            "scan",
            require_latest=True,
        )


def test_source_scan_entry_rejects_missing_identity_and_entry_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RosterSyncError, match="source scan not found"):
        subject._validated_source_scan_entry(_QueueConnection([]), "scan", "agent.md")
    with pytest.raises(RosterSyncError, match="identity is invalid"):
        subject._validated_source_scan_entry(
            _QueueConnection([_scan_row(id="other")]),
            "scan",
            "agent.md",
        )

    monkeypatch.setattr(
        subject,
        "_validated_source_scan_declaration",
        lambda *_args, **_kwargs: ({}, "partial"),
    )
    monkeypatch.setattr(
        subject,
        "_validated_source_scan_header",
        lambda *_args, **_kwargs: _header_row(),
    )
    monkeypatch.setattr(
        subject,
        "_source_scan_structural_evidence",
        lambda *_args, **_kwargs: {"header": {"event_order": 2}},
    )
    with pytest.raises(RosterSyncError, match="entry evidence is invalid"):
        subject._validated_source_scan_entry(
            _QueueConnection([_scan_row()], []),
            "scan",
            "agent.md",
        )

    invalid_entry = {
        "relative_path": "agent.md",
        "slug": "agent",
        "content_hash": "1" * 64,
        "status": "invalid",
        "candidate_id": None,
    }
    with pytest.raises(RosterSyncError, match="entry evidence is invalid"):
        subject._validated_source_scan_entry(
            _QueueConnection([_scan_row()], [invalid_entry]),
            "scan",
            "agent.md",
        )


def _queued_row_and_download(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    downloaded = _unknown_manifest(root)
    store = Store(root / "agency.db")
    source_id = store.add_agent_source(str(root / "source"), "coverage-source")
    subject.quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
            "FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_queued'"
        ).fetchone()
        detail = json.loads(row["detail"])
        download = conn.execute(
            "SELECT d.source_id, d.slug, d.hash, d.content, d.status, "
            "c.id AS candidate_id FROM agent_downloads d "
            "LEFT JOIN agent_candidates c ON c.download_id = d.id WHERE d.id = ?",
            (detail["download_id"],),
        ).fetchone()
        return dict(row), dict(download)
    finally:
        conn.close()


def test_queue_item_rejects_non_text_download_and_invalid_order(tmp_path: Path) -> None:
    row, download = _queued_row_and_download(tmp_path)
    with pytest.raises(RosterSyncError, match="download content must be text"):
        subject._validated_remediation_queue_item_base(
            _QueueConnection([{**download, "content": b"bytes"}]),
            row,
        )
    with pytest.raises(RosterSyncError, match="event order is invalid"):
        subject._validated_remediation_queue_item_base(
            _QueueConnection([download]),
            {**row, "event_order": True},
        )


def test_queue_scan_binding_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    item = {
        "source_id": "source",
        "scan_id": "scan",
        "relative_path": "agent.md",
        "slug": "agent",
        "receipt": {"original_hash": "1" * 64},
        "created_at": "2026-07-18T12:00:00+00:00",
        "_event_order": 1,
    }
    monkeypatch.setattr(
        subject,
        "_validated_remediation_queue_item_base",
        lambda *_args: item,
    )
    monkeypatch.setattr(
        subject,
        "_cached_remediation_source_scan",
        lambda *_args: {
            "source_id": "other",
            "entries": [],
            "created_at": item["created_at"],
            "_event_order": 2,
        },
    )
    with pytest.raises(RosterSyncError, match="source scan binding is invalid"):
        subject._validated_remediation_queue_item(object(), {})


def test_remediated_resolution_rejects_mismatched_transformation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = SimpleNamespace(
        event_order=2,
        event_created_at="2026-07-18T12:00:00+00:00",
        candidate_download_id="different",
        candidate_hash="2" * 64,
        source_id="source",
        source_slug="agent",
        source_hash="1" * 64,
        source_content="original",
        source_status="quarantined",
        origin="agent.md",
        relative_path="agent.md",
    )
    monkeypatch.setattr(
        subject,
        "candidate_remediation_evidence_from_connection",
        lambda *_args: evidence,
    )
    with pytest.raises(RosterSyncError, match="transformation evidence is invalid"):
        subject._validate_remediated_resolution_provenance(
            object(),
            {
                "created_at": "2026-07-18T12:00:00+00:00",
                "event_order": 3,
            },
            {
                "candidate_download_id": "candidate-download",
                "candidate_hash": "2" * 64,
                "original_hash": "1" * 64,
            },
            {
                "created_at": "2026-07-18T12:00:00+00:00",
                "_event_order": 1,
                "source_id": "source",
                "slug": "agent",
                "_source_content": "original",
                "origin": "agent.md",
                "relative_path": "agent.md",
            },
            {"id": "candidate"},
        )


def test_candidate_and_audit_cache_wrap_lookup_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = {
        "candidate_id": "candidate",
        "audit_id": "audit",
    }

    def missing_candidate(*_args: Any) -> Any:
        raise KeyError("missing")

    monkeypatch.setattr(subject, "candidate_record_from_connection", missing_candidate)
    with pytest.raises(RosterSyncError, match="candidate evidence is invalid"):
        subject._cached_resolution_candidate_audit(object(), detail, None, None)

    candidate = {
        "id": "candidate",
        "version": "v1",
        "hash": "1" * 64,
    }
    monkeypatch.setattr(subject, "candidate_record_from_connection", lambda *_args: candidate)

    def missing_audit(*_args: Any, **_kwargs: Any) -> Any:
        raise RosterSyncError("missing")

    monkeypatch.setattr(subject, "assert_bound_candidate_audit_from_connection", missing_audit)
    with pytest.raises(RosterSyncError, match="candidate evidence is invalid"):
        subject._cached_resolution_candidate_audit(object(), detail, None, None)


def _resolution_detail(**overrides: Any) -> dict[str, Any]:
    detail = {
        "audit_id": "audit",
        "audit_revision": "sha256:" + "1" * 64,
        "candidate_download_id": "candidate-download",
        "candidate_hash": "2" * 64,
        "candidate_id": "candidate",
        "download_id": "download",
        "original_hash": "3" * 64,
        "origin": "agent.md",
        "policy_hash": "4" * 64,
        "queue_event_id": "queue",
        "relative_path": "agent.md",
        "resolution": "superseded_by_candidate",
        "scan_id": "candidate-scan",
        "source_hash": "5" * 64,
        "source_id": "source",
    }
    detail.update(overrides)
    return detail


def _resolution_queue() -> dict[str, Any]:
    return {
        "slug": "agent",
        "_event_order": 1,
        "event_id": "queue",
        "download_id": "download",
        "source_id": "source",
        "origin": "agent.md",
        "relative_path": "agent.md",
        "receipt": {"original_hash": "3" * 64},
        "created_at": "2026-07-18T12:00:00+00:00",
        "_authority_dependencies": [],
    }


def test_resolution_rejects_order_binding_disposition_and_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _resolution_queue()
    row = {
        "id": "resolution",
        "agent_slug": "agent",
        "created_at": "2026-07-18T12:00:00+00:00",
        "event_order": 3,
        "detail": "{}",
    }
    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution_detail",
        lambda *_args: _resolution_detail(),
    )
    with pytest.raises(RosterSyncError, match="event order is invalid"):
        subject._validated_remediation_resolution(
            object(),
            {**row, "event_order": True},
            queue,
        )
    with pytest.raises(RosterSyncError, match="queue binding is invalid"):
        subject._validated_remediation_resolution(
            object(),
            {**row, "agent_slug": "other"},
            queue,
        )

    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution_detail",
        lambda *_args: _resolution_detail(resolution="remediated_candidate"),
    )
    with pytest.raises(RosterSyncError, match="disposition is invalid"):
        subject._validated_remediation_resolution(object(), row, queue)

    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution_detail",
        lambda *_args: _resolution_detail(),
    )
    monkeypatch.setattr(
        subject,
        "_cached_resolution_candidate_audit",
        lambda *_args: (
            {
                "id": "candidate",
                "download_id": "wrong",
                "hash": "2" * 64,
                "download_hash": "2" * 64,
                "source_id": "source",
                "prompt_path": "agent.md",
            },
            {
                "created_at": row["created_at"],
                "audit_revision": "sha256:" + "1" * 64,
                "policy_hash": "4" * 64,
            },
            True,
        ),
    )
    monkeypatch.setattr(
        subject,
        "_cached_remediation_source_scan",
        lambda *_args: {
            "id": "candidate-scan",
            "source_id": "source",
            "created_at": row["created_at"],
            "_event_order": 2,
            "_authority_dependencies": [],
            "entries": [
                {
                    "relative_path": "agent.md",
                    "content_hash": "5" * 64,
                    "status": "candidate",
                    "candidate_id": "candidate",
                }
            ],
        },
    )
    with pytest.raises(RosterSyncError, match="candidate evidence is invalid"):
        subject._validated_remediation_resolution(object(), row, queue)


def test_prepare_resolution_authority_rejects_changed_scan_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = {
        **_resolution_queue(),
        "scan_id": "queue-scan",
    }
    detail = _resolution_detail()
    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution",
        lambda *_args, **_kwargs: {"_authority_dependencies": []},
    )
    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution_detail",
        lambda *_args: detail,
    )
    monkeypatch.setattr(
        subject,
        "_cached_remediation_source_scan",
        lambda *_args: {},
    )
    monkeypatch.setattr(
        subject,
        "_cached_full_remediation_source_scan",
        lambda *_args: {"_authority_hash": "1" * 64},
    )
    monkeypatch.setattr(
        subject,
        "_assert_local_scan_entry_matches_full_scan",
        lambda *_args, **_kwargs: {
            "status": "ignored",
            "slug": "agent",
            "content_hash": "3" * 64,
        },
    )
    with pytest.raises(RosterSyncError, match="source scan entry changed"):
        subject._prepare_remediation_resolution_authority(
            object(),
            {"detail": "{}"},
            queue,
        )


def test_persist_authority_rejects_validation_before_resolution() -> None:
    store = SimpleNamespace(_now=lambda: "2026-07-18T11:59:59+00:00")
    with pytest.raises(RosterSyncError, match="predates its resolution"):
        subject._persist_remediation_resolution_authority(
            object(),
            store,
            {"detail": "{}"},
            {"created_at": "2026-07-18T12:00:00+00:00"},
            {"created_at": "2026-07-18T12:00:00+00:00"},
        )


def _history_row(event_id: str, queue_event_id: str | None) -> dict[str, Any]:
    detail: Any = {} if queue_event_id is None else {"queue_event_id": queue_event_id}
    return {
        "event_order": 3,
        "id": event_id,
        "agent_slug": "agent",
        "detail": json.dumps(detail),
        "created_at": "2026-07-18T12:00:00+00:00",
    }


def _patch_queue_snapshot_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "_assert_remediation_authority_available", lambda _conn: None)
    monkeypatch.setattr(subject, "_remediation_cursor_order", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subject, "current_active_basis_hash_from_connection", lambda _conn: "basis")


def test_queue_snapshot_rejects_invalid_or_unknown_history_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_queue_snapshot_shell(monkeypatch)
    with pytest.raises(RosterSyncError, match="queue binding is invalid"):
        subject._remediation_queue_snapshot(
            _QueueConnection([], [_history_row("resolution", None)]),
            limit=1,
        )

    with pytest.raises(RosterSyncError, match="unknown queue event"):
        subject._remediation_queue_snapshot(
            _QueueConnection([], [_history_row("resolution", "queue")], []),
            limit=1,
        )


def test_queue_snapshot_reuses_queue_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_queue_snapshot_shell(monkeypatch)
    monkeypatch.setattr(
        subject,
        "_validated_remediation_queue_item",
        lambda *_args, **_kwargs: {"event_id": "queue"},
    )
    monkeypatch.setattr(
        subject,
        "_validated_remediation_resolution",
        lambda _conn, row, _queue, **_kwargs: {"event_id": row["id"]},
    )
    rows = [
        _history_row("resolution-1", "queue"),
        _history_row("resolution-2", "queue"),
    ]
    snapshot = subject._remediation_queue_snapshot(
        _QueueConnection(
            [],
            rows,
            [{"id": "queue"}],
            [],
            [
                {
                    "event_order": 3,
                    "id": "resolution-1",
                    "queue_event_id": "queue",
                },
                {
                    "event_order": 3,
                    "id": "resolution-2",
                    "queue_event_id": "queue",
                },
            ],
            [(2,)],
            [(2,)],
        ),
        limit=2,
    )
    assert [item["event_id"] for item in snapshot["history"]] == [
        "resolution-1",
        "resolution-2",
    ]


def test_eligible_resolution_requires_current_audit_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = SimpleNamespace(
        status="candidate",
        slug="agent",
        relative_path="agent.md",
        origin="agent.md",
    )
    monkeypatch.setattr(
        subject,
        "candidate_record_from_connection",
        lambda *_args: {"id": "candidate"},
    )
    monkeypatch.setattr(
        subject,
        "assert_candidate_audits_current",
        lambda *_args, **_kwargs: {"candidate": "other-audit"},
    )
    with pytest.raises(RosterSyncError, match="current audit basis"):
        subject._eligible_remediation_candidate_identities(
            object(),
            "source",
            [outcome],
            {"agent": {"slug": "agent"}},
            {"agent": ("candidate", "candidate-download")},
            {"candidate": {"id": "audit", "verdict": "passed"}},
        )


def _resolution_selection(
    *,
    source_hash: str = "2" * 64,
    remediation: Any = None,
) -> tuple[Any, dict[str, Any], str, str, dict[str, Any]]:
    return (
        SimpleNamespace(content_hash=source_hash, remediation=remediation),
        {"hash": "4" * 64},
        "candidate",
        "candidate-download",
        {
            "id": "audit",
            "audit_revision": "sha256:" + "5" * 64,
            "policy_hash": "6" * 64,
            "created_at": "2026-07-18T12:00:00+00:00",
        },
    )


def _queued_resolution_item(**overrides: Any) -> dict[str, Any]:
    item = {
        "source_id": "source",
        "relative_path": "agent.md",
        "origin": "agent.md",
        "slug": "agent",
        "receipt": {"original_hash": "1" * 64},
        "download_id": "download",
        "event_id": "queue",
        "created_at": "2026-07-18T12:00:00+00:00",
    }
    item.update(overrides)
    return item


def _record_resolution_connection(
    *,
    pending_rows: list[Any],
    candidate_scan_row: Any = None,
    existing_resolutions: list[Any] | None = None,
    resolution_row: Any = None,
) -> _RouterConnection:
    def route(sql: str, _parameters: Any) -> list[Any]:
        if "FROM current_remediation_identities AS identity" in sql:
            return pending_rows
        if "SELECT created_at FROM agent_source_scans" in sql:
            return [] if candidate_scan_row is None else [candidate_scan_row]
        if "INDEXED BY idx_agent_import_resolution_queue" in sql:
            return existing_resolutions or []
        if "FROM agent_import_events WHERE id = ?" in sql:
            return [] if resolution_row is None else [resolution_row]
        return []

    return _RouterConnection(route)


def _patch_record_resolution_shell(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selected: tuple[Any, dict[str, Any], str, str, dict[str, Any]],
    queued: dict[str, Any],
) -> None:
    identity = ("source", "agent.md", "agent.md")
    monkeypatch.setattr(subject, "_assert_remediation_authority_available", lambda _conn: None)
    monkeypatch.setattr(
        subject,
        "_eligible_remediation_candidate_identities",
        lambda *_args: {identity: selected},
    )
    monkeypatch.setattr(
        subject,
        "_validated_remediation_queue_item",
        lambda *_args, **_kwargs: queued,
    )


def _record_resolutions(
    conn: Any,
    store: Any,
) -> bool:
    return subject._record_candidate_remediation_resolutions(
        conn,
        store,
        "source",
        [],
        {},
        {},
        {},
        scan_id="candidate-scan",
    )


def test_record_resolution_rejects_unbound_queue_and_missing_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _resolution_selection()
    queued = _queued_resolution_item(source_id="other")
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    with pytest.raises(RosterSyncError, match="unbound queue item"):
        _record_resolutions(
            _record_resolution_connection(pending_rows=[{"id": "queue"}]),
            SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
        )

    queued = _queued_resolution_item()
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    with pytest.raises(RosterSyncError, match="source scan is unavailable"):
        _record_resolutions(
            _record_resolution_connection(pending_rows=[{"id": "queue"}]),
            SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
        )


def test_record_resolution_skips_unchanged_and_records_deferred_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _resolution_selection(source_hash="1" * 64)
    queued = _queued_resolution_item()
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    monkeypatch.setattr(subject, "MAX_REMEDIATION_RESOLUTIONS_PER_SYNC", 1)
    events: list[str] = []
    monkeypatch.setattr(
        subject,
        "_record_import_event",
        lambda _conn, _store, event_type, *_args, **_kwargs: events.append(event_type) or "event",
    )
    assert _record_resolutions(
        _record_resolution_connection(pending_rows=[{"id": "one"}, {"id": "two"}]),
        SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
    )
    assert events == ["manifest_remediation_resolution_batch_deferred"]


def test_record_resolution_rejects_future_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _resolution_selection()
    queued = _queued_resolution_item()
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    with pytest.raises(RosterSyncError, match="timestamp is in the future"):
        _record_resolutions(
            _record_resolution_connection(
                pending_rows=[{"id": "queue"}],
                candidate_scan_row={"created_at": "2026-07-18T12:00:01+00:00"},
            ),
            SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
        )


def test_record_resolution_reuses_one_valid_existing_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _resolution_selection()
    queued = _queued_resolution_item()
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    bad = {"id": "bad"}
    good = {"id": "good"}

    def prepare(_conn: Any, row: Any, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        if row is bad:
            raise RosterSyncError("invalid")
        return {"event_id": "good"}

    monkeypatch.setattr(subject, "_prepare_remediation_resolution_authority", prepare)
    persisted: list[str] = []
    monkeypatch.setattr(
        subject,
        "_persist_remediation_resolution_authority",
        lambda _conn, _store, row, *_args: persisted.append(row["id"]),
    )
    assert not _record_resolutions(
        _record_resolution_connection(
            pending_rows=[{"id": "queue"}],
            candidate_scan_row={"created_at": "2026-07-18T12:00:00+00:00"},
            existing_resolutions=[bad, good],
        ),
        SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
    )
    assert persisted == ["good"]


def test_record_resolution_requires_persisted_new_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _resolution_selection()
    queued = _queued_resolution_item()
    _patch_record_resolution_shell(monkeypatch, selected=selected, queued=queued)
    monkeypatch.setattr(subject, "_record_import_event", lambda *_args, **_kwargs: "new-event")
    with pytest.raises(RosterSyncError, match="event was not persisted"):
        _record_resolutions(
            _record_resolution_connection(
                pending_rows=[{"id": "queue"}],
                candidate_scan_row={"created_at": "2026-07-18T12:00:00+00:00"},
            ),
            SimpleNamespace(_now=lambda: "2026-07-18T12:00:00+00:00"),
        )


@pytest.mark.parametrize(
    ("active", "scan", "message"),
    [
        ({}, {"source_id": "source", "entries": []}, "inactive agent"),
        (
            {"agent": {"agent_slug": "agent", "source_id": "other"}},
            {"source_id": "source", "entries": []},
            "not owned",
        ),
        (
            {"agent": {"agent_slug": "agent", "source_id": "source"}},
            {"source_id": "source", "entries": [{"slug": "agent"}]},
            "still present",
        ),
    ],
)
def test_retirement_diff_rejects_invalid_active_ownership(
    monkeypatch: pytest.MonkeyPatch,
    active: dict[str, Any],
    scan: dict[str, Any],
    message: str,
) -> None:
    conn = _TransactionConnection()
    monkeypatch.setattr(subject, "_connect", lambda _store: conn)
    monkeypatch.setattr(
        subject,
        "_validated_source_scan",
        lambda *_args, **_kwargs: {
            "id": "scan",
            "status": "complete",
            **scan,
        },
    )
    monkeypatch.setattr(subject, "_active_from_connection", lambda _conn: active)
    with pytest.raises(RosterSyncError, match=message):
        subject.create_retirement_diff(object(), scan_id="scan", slugs=["agent"])
    assert conn.rolled_back and conn.closed


def test_retirement_diff_rejects_missing_active_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _TransactionConnection()
    monkeypatch.setattr(subject, "_connect", lambda _store: conn)
    monkeypatch.setattr(
        subject,
        "_validated_source_scan",
        lambda *_args, **_kwargs: {
            "id": "scan",
            "status": "complete",
            "source_id": "source",
            "entries": [],
        },
    )
    monkeypatch.setattr(
        subject,
        "_active_from_connection",
        lambda _conn: {
            "agent": {
                "agent_slug": "agent",
                "source_id": "source",
            }
        },
    )
    monkeypatch.setattr(subject, "_active_agent_fingerprint", lambda _agent: None)
    with pytest.raises(RosterSyncError, match="no active revision identity"):
        subject.create_retirement_diff(object(), scan_id="scan", slugs=["agent"])


def test_candidate_record_rejects_download_source_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "id": "candidate",
        "download_id": "download",
        "slug": "agent",
        "name": "Agent",
        "description": "description",
        "division": "engineering",
        "prompt_path": "agent.md",
        "source": "source",
        "source_id": "source",
        "source_version": "v1",
        "version": "v1",
        "hash": subject._hash_text("content"),
        "content": "content",
        "categories": [],
        "capabilities": [],
        "tool_affinity": [],
    }
    record = {
        **candidate,
        "status": "pending",
        "download_status": "quarantined",
        "download_source_id": "other",
        "download_content": "content",
        "download_hash": candidate["hash"],
    }
    monkeypatch.setattr(
        subject,
        "_candidate_records",
        lambda *_args: {"candidate": record},
    )
    with pytest.raises(RosterSyncError, match="source no longer matches"):
        subject._assert_candidate_records(
            object(),
            [candidate],
            allowed_statuses=frozenset({"pending"}),
        )


def _retirement(slug: str = "agent", **overrides: Any) -> dict[str, str]:
    item = {
        "slug": slug,
        "scan_id": "scan",
        "source_id": "source",
        "version": "v1",
        "hash": "1" * 64,
    }
    item.update(overrides)
    return item


@pytest.mark.parametrize(
    ("scan", "active_rows", "message"),
    [
        (
            {"status": "partial", "source_id": "source", "entries": []},
            [],
            "partial",
        ),
        (
            {"status": "complete", "source_id": "other", "entries": []},
            [],
            "source does not match",
        ),
        (
            {
                "status": "complete",
                "source_id": "source",
                "entries": [{"slug": "agent"}],
            },
            [],
            "still present",
        ),
        (
            {"status": "complete", "source_id": "source", "entries": []},
            [],
            "inactive agent",
        ),
        (
            {"status": "complete", "source_id": "source", "entries": []},
            [{"source_id": "other", "version": "v1", "hash": "1" * 64}],
            "no longer matches",
        ),
    ],
)
def test_retirement_evidence_rejects_invalid_scan_or_active_record(
    monkeypatch: pytest.MonkeyPatch,
    scan: dict[str, Any],
    active_rows: list[Any],
    message: str,
) -> None:
    monkeypatch.setattr(subject, "_validated_source_scan", lambda *_args, **_kwargs: scan)
    with pytest.raises(RosterSyncError, match=message):
        subject._assert_retirement_evidence(
            _QueueConnection(active_rows),
            [_retirement()],
        )


def test_retirement_evidence_reuses_validated_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def scan(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"status": "complete", "source_id": "source", "entries": []}

    monkeypatch.setattr(subject, "_validated_source_scan", scan)
    subject._assert_retirement_evidence(
        _QueueConnection(
            [{"source_id": "source", "version": "v1", "hash": "1" * 64}],
            [{"source_id": "source", "version": "v1", "hash": "1" * 64}],
        ),
        [_retirement("one"), _retirement("two")],
    )
    assert calls == 1


def test_approve_already_approved_retirement_only_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _TransactionConnection()
    monkeypatch.setattr(subject, "_connect", lambda _store: conn)
    monkeypatch.setattr(
        subject,
        "_snapshot_from_connection",
        lambda *_args: (
            {
                "approved": True,
                "candidates": [],
                "retirements": [_retirement()],
            },
            False,
        ),
    )
    monkeypatch.setattr(subject, "_assert_retirement_evidence", lambda *_args: None)
    subject.approve_snapshot(object(), "snapshot")
    assert conn.committed and conn.closed


def test_activate_rejects_changed_previously_activated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _TransactionConnection()
    retirement = _retirement()
    monkeypatch.setattr(subject, "_connect", lambda _store: conn)
    monkeypatch.setattr(
        subject,
        "_snapshot_from_connection",
        lambda *_args: (
            {
                "approved": True,
                "candidates": [],
                "retirements": [retirement],
            },
            True,
        ),
    )
    monkeypatch.setattr(
        subject,
        "_active_from_connection",
        lambda _conn: {"agent": {"agent_slug": "agent"}},
    )
    with pytest.raises(RosterSyncError, match="already activated but its touched agents changed"):
        subject.activate_snapshot(object(), "snapshot")


def _patch_activation_shell(
    monkeypatch: pytest.MonkeyPatch,
    conn: _TransactionConnection,
    manifest: dict[str, Any],
) -> None:
    monkeypatch.setattr(subject, "_connect", lambda _store: conn)
    monkeypatch.setattr(
        subject,
        "_snapshot_from_connection",
        lambda *_args: (manifest, False),
    )
    monkeypatch.setattr(subject, "_assert_candidate_records", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subject, "_assert_retirement_evidence", lambda *_args: None)
    monkeypatch.setattr(subject, "_assert_snapshot_active_basis", lambda *_args: None)
    monkeypatch.setattr(subject, "_preflight_candidate_versions", lambda *_args: set())
    monkeypatch.setattr(subject, "_apply_candidate_delta", lambda *_args: False)
    monkeypatch.setattr(subject, "_apply_retirement_delta", lambda *_args: False)
    monkeypatch.setattr(subject, "_record_import_event", lambda *_args, **_kwargs: "event")


def test_activation_skips_duplicate_status_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"id": "candidate", "slug": "agent", "download_id": "download"}

    def route(sql: str, _parameters: Any) -> list[Any]:
        if "SELECT status FROM agent_candidates" in sql:
            return [{"status": "activated"}]
        if "SELECT manifest FROM agent_snapshots" in sql:
            return [{"manifest": "{}"}]
        return []

    conn = _RouterConnection(route)
    manifest = {
        "approved": True,
        "candidates": [candidate],
        "retirements": [],
        "active_basis": {"agent": "fingerprint"},
    }
    _patch_activation_shell(monkeypatch, conn, manifest)
    monkeypatch.setattr(subject, "_active_from_connection", lambda _conn: {"agent": candidate})
    monkeypatch.setattr(
        subject,
        "_active_agent_fingerprint",
        lambda agent: None if agent is None else "fingerprint",
    )
    monkeypatch.setattr(
        subject,
        "refresh_candidate_audit_basis_in_connection",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        subject,
        "assert_candidate_audits_current",
        lambda *_args, **_kwargs: {"candidate": "audit-" + "1" * 64},
    )
    status_events: list[str] = []
    monkeypatch.setattr(
        subject,
        "record_candidate_status_event",
        lambda *_args, **_kwargs: status_events.append("status"),
    )
    subject.activate_snapshot(object(), "snapshot")
    assert status_events == []
    assert conn.committed


def test_activation_rejects_disappearing_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _TransactionConnection()
    manifest = {
        "approved": True,
        "candidates": [],
        "retirements": [_retirement()],
        "active_basis": {"agent": "fingerprint"},
    }
    _patch_activation_shell(monkeypatch, conn, manifest)
    monkeypatch.setattr(
        subject,
        "_active_from_connection",
        lambda _conn: {"agent": {"agent_slug": "agent"}},
    )
    with pytest.raises(RosterSyncError, match="disappeared during activation"):
        subject.activate_snapshot(object(), "snapshot")


def test_remaining_empty_and_uncached_branch_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "id": "candidate",
        "version": "v1",
        "hash": "1" * 64,
    }
    audit = {"id": "audit"}
    monkeypatch.setattr(subject, "candidate_record_from_connection", lambda *_args: candidate)
    monkeypatch.setattr(
        subject,
        "assert_bound_candidate_audit_from_connection",
        lambda *_args, **_kwargs: (audit, True),
    )
    assert subject._cached_resolution_candidate_audit(
        object(),
        {"candidate_id": "candidate", "audit_id": "audit"},
        None,
        None,
    ) == (candidate, audit, True)

    subject._validate_manifest_candidate_identity(
        [{"slug": "agent"}],
        ["candidate"],
        ["candidate"],
        snapshot_id="snapshot",
    )
    monkeypatch.setattr(subject, "_candidate_records", lambda *_args: {})
    subject._assert_candidate_records(object(), [], allowed_statuses=frozenset())
    subject._assert_snapshot_active_basis("snapshot", {}, {})
