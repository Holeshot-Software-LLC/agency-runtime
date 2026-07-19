"""Focused contracts for documentation front-matter schema variants."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts import verify_docs


def _base_meta(**overrides: Any) -> dict[str, object]:
    meta: dict[str, object] = {
        "title": "Schema fixture",
        "status": "active",
        "category": "testing",
        "created": "2026-07-10",
        "updated": "2026-07-12",
        "tags": [],
        "related": [],
        "supersedes": [],
        "superseded_by": None,
    }
    meta.update(overrides)
    return meta


def _document(
    meta: dict[str, object],
    relative: str = "docs/testing/schema-fixture.md",
) -> verify_docs.Document:
    return verify_docs.Document(
        path=verify_docs.ROOT / relative,
        meta=meta,
        body="# Schema fixture",
    )


def _errors(doc: verify_docs.Document) -> list[str]:
    errors: list[str] = []
    verify_docs.validate_schema(doc, errors)
    return errors


@pytest.mark.parametrize(
    "meta",
    [
        _base_meta(),
        _base_meta(
            type="issue",
            status="open",
            epic="runtime",
            issue_id="AR-99",
            priority="p1",
            tracker_url=None,
            depends_on=[],
            blocks=[],
        ),
        _base_meta(
            type="worklog",
            commit="a" * 40,
            short="a" * 7,
            date="2026-07-12",
            pr=None,
            related_issues=[],
        ),
        _base_meta(
            id="ADR-0099",
            type="decision",
            status="accepted",
            deciders=[],
        ),
        _base_meta(created=date(2026, 7, 10), updated=date(2026, 7, 12)),
    ],
)
def test_valid_general_and_variant_schemas_have_no_errors(
    meta: dict[str, object],
) -> None:
    assert _errors(_document(meta)) == []


def test_issue_schema_reports_missing_and_invalid_fields_in_stable_order() -> None:
    doc = _document(
        _base_meta(
            type="issue",
            status="invalid",
            issue_id="AR-1",
            priority="p4",
            depends_on="AR-01",
            blocks=None,
        )
    )

    assert _errors(doc) == [
        f"{doc.relative}: missing front-matter field 'epic'",
        f"{doc.relative}: missing front-matter field 'tracker_url'",
        f"{doc.relative}: invalid issue status 'invalid'",
        f"{doc.relative}: issue_id must match AR-NN",
        f"{doc.relative}: priority must be p0, p1, p2, or p3",
        f"{doc.relative}: depends_on must be a list",
        f"{doc.relative}: blocks must be a list",
    ]


def test_worklog_schema_reports_its_own_status_and_list_contracts() -> None:
    doc = _document(
        _base_meta(
            type="worklog",
            status="proposed",
            short="abc1234",
            date="2026-07-12",
            related_issues="AR-01",
        )
    )

    assert _errors(doc) == [
        f"{doc.relative}: missing front-matter field 'commit'",
        f"{doc.relative}: missing front-matter field 'pr'",
        f"{doc.relative}: invalid worklog status 'proposed'",
        f"{doc.relative}: related_issues must be a list",
    ]


def test_decision_schema_reports_identity_status_and_decider_contracts() -> None:
    doc = _document(_base_meta(type="decision", status="active"))

    assert _errors(doc) == [
        f"{doc.relative}: missing front-matter field 'deciders'",
        f"{doc.relative}: missing front-matter field 'id'",
        f"{doc.relative}: invalid decision status 'active'",
        f"{doc.relative}: decision id must match ADR-NNNN",
        f"{doc.relative}: deciders must be a list",
    ]


def test_general_schema_reports_common_type_date_and_ordering_errors() -> None:
    doc = _document(
        _base_meta(
            title="",
            category=None,
            created="2026-07-12",
            updated="2026-07-10",
            tags="testing",
            related=None,
            supersedes="ADR-0001",
            superseded_by=[],
            status="unknown",
        )
    )

    assert _errors(doc) == [
        f"{doc.relative}: title must be a non-empty string",
        f"{doc.relative}: category must be a non-empty string",
        f"{doc.relative}: updated precedes created",
        f"{doc.relative}: tags must be a list",
        f"{doc.relative}: related must be a list",
        f"{doc.relative}: supersedes must be a list",
        f"{doc.relative}: superseded_by must be a string or null",
        f"{doc.relative}: invalid general-document status 'unknown'",
    ]


def test_invalid_dates_are_reported_without_an_ordering_error() -> None:
    doc = _document(_base_meta(created="07/10/2026", updated=20260712))

    assert _errors(doc) == [
        f"{doc.relative}: created must be YYYY-MM-DD",
        f"{doc.relative}: updated must be YYYY-MM-DD",
    ]


def test_retired_schema_requires_archive_metadata_and_successor() -> None:
    doc = _document(_base_meta(status="retired"))

    assert _errors(doc) == [
        f"{doc.relative}: missing front-matter field 'retired'",
        f"{doc.relative}: missing front-matter field 'retired_reason'",
        f"{doc.relative}: retired document must live in category archive/",
        f"{doc.relative}: retired must be YYYY-MM-DD",
        f"{doc.relative}: retired document needs superseded_by",
    ]


def test_retired_schema_accepts_complete_category_archive_record() -> None:
    doc = _document(
        _base_meta(
            status="retired",
            retired="2026-07-12",
            retired_reason="Replaced",
            superseded_by="docs/testing/replacement.md",
        ),
        relative="docs/testing/archive/schema-fixture.md",
    )

    assert _errors(doc) == []


def test_variant_helpers_are_deterministic_and_do_not_mutate_metadata() -> None:
    doc = _document(
        _base_meta(
            type="issue",
            status="open",
            epic="runtime",
            issue_id="AR-99",
            priority="p1",
            tracker_url=None,
            depends_on=[],
            blocks=[],
        )
    )
    before = deepcopy(doc.meta)

    first = verify_docs._issue_schema_errors(doc)
    second = verify_docs._issue_schema_errors(doc)

    assert first == second == []
    assert doc.meta == before


def test_validate_schema_appends_without_replacing_existing_errors() -> None:
    doc = _document(_base_meta(status="unknown"))
    errors = ["existing error"]

    verify_docs.validate_schema(doc, errors)

    assert errors == [
        "existing error",
        f"{doc.relative}: invalid general-document status 'unknown'",
    ]


def _decision(
    decision_id: str,
    *,
    supersedes: list[str] | None = None,
    superseded_by: str | None = None,
) -> verify_docs.Document:
    return _document(
        _base_meta(
            id=decision_id,
            type="decision",
            status="accepted",
            deciders=[],
            supersedes=supersedes or [],
            superseded_by=superseded_by,
        ),
        relative=f"docs/decisions/{decision_id.lower()}-fixture.md",
    )


def test_decision_relation_helper_wires_reciprocal_chain_without_errors() -> None:
    old = _decision("ADR-0001", superseded_by="ADR-0002")
    new = _decision("ADR-0002", supersedes=[old.relative])
    by_id = {"ADR-0001": old, "ADR-0002": new}
    by_path = {doc.path.name: decision_id for decision_id, doc in by_id.items()}
    graph = {decision_id: set() for decision_id in by_id}

    errors = verify_docs._decision_relation_errors("ADR-0002", new, by_id, by_path, graph)

    assert errors == []
    assert graph == {"ADR-0001": set(), "ADR-0002": {"ADR-0001"}}


def test_decision_relation_helper_reports_unknown_and_nonreciprocal_links() -> None:
    old = _decision("ADR-0001")
    peer = _decision("ADR-0002")
    broken = _decision(
        "ADR-0003",
        supersedes=["ADR-0001", "ADR-9999"],
        superseded_by="ADR-0002",
    )
    by_id = {"ADR-0001": old, "ADR-0002": peer, "ADR-0003": broken}
    by_path = {doc.path.name: decision_id for decision_id, doc in by_id.items()}
    graph = {decision_id: set() for decision_id in by_id}

    errors = verify_docs._decision_relation_errors("ADR-0003", broken, by_id, by_path, graph)

    assert errors == [
        f"{broken.relative}: ADR-0001 does not reciprocate superseded_by=ADR-0003",
        f"{broken.relative}: unknown supersedes reference 'ADR-9999'",
        f"{broken.relative}: ADR-0002 does not reciprocate supersedes=ADR-0003",
    ]
    assert graph["ADR-0003"] == {"ADR-0001"}


def test_legal_notice_can_preserve_source_name_without_cross_repo_linkage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    path = tmp_path / "THIRD_PARTY_NOTICES.md"
    text = "Agency-agents source provenance; maintained by msitarzewski."
    path.write_text(text, encoding="utf-8")
    doc = verify_docs.Document(path=path, meta={}, body=text)
    errors: list[str] = []

    verify_docs.validate_links_and_boundaries(doc, errors)

    assert errors == []


def test_legal_notice_exemption_does_not_allow_cross_repository_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    path = tmp_path / "THIRD_PARTY_NOTICES.md"
    text = "https://github.com/example/agency-agents"
    path.write_text(text, encoding="utf-8")
    doc = verify_docs.Document(path=path, meta={}, body=text)
    errors: list[str] = []

    verify_docs.validate_links_and_boundaries(doc, errors)

    assert errors == [
        "THIRD_PARTY_NOTICES.md: cross-repository GitHub URL is not allowed (example/agency-agents)"
    ]


def test_legacy_source_names_remain_forbidden_outside_legal_notice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    path = tmp_path / "README.md"
    text = "agency-agents maintained by msitarzewski"
    path.write_text(text, encoding="utf-8")
    doc = verify_docs.Document(path=path, meta={}, body=text)
    errors: list[str] = []

    verify_docs.validate_links_and_boundaries(doc, errors)

    assert errors == [
        "README.md: contains legacy sibling repository name",
        "README.md: contains legacy sibling owner",
    ]
