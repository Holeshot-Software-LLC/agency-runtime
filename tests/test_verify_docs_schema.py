"""Focused contracts for documentation front-matter schema variants."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts import verify_docs
from scripts.worklog_history import stable_short_shas


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
        _base_meta(
            type="handoff",
            issue_id="AR-119",
            branch="codex/ar-119",
            evidence_commit="a" * 40,
            hard_checkpoint_percent=50,
            minimum_ledger_commit="b" * 40,
            tracker_url="https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132",
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


def test_handoff_schema_reports_invalid_checkpoint_fields() -> None:
    doc = _document(
        _base_meta(
            type="handoff",
            status="draft",
            issue_id="AR-1",
            branch="invalid branch",
            evidence_commit="abc",
            hard_checkpoint_percent=51,
            live_evaluation_admission_percent=64,
            minimum_ledger_commit=None,
            tracker_url=[],
        ),
        relative="docs/roadmap/handoffs/issue-AR-1.md",
    )

    assert _errors(doc) == [
        f"{doc.relative}: active handoff status must be 'active'",
        f"{doc.relative}: handoff issue_id must match AR-NN",
        f"{doc.relative}: branch must be a non-empty Git ref name",
        f"{doc.relative}: evidence_commit must be a full lowercase Git SHA",
        f"{doc.relative}: minimum_ledger_commit must be a full lowercase Git SHA",
        f"{doc.relative}: tracker_url must be a string or null",
        f"{doc.relative}: hard_checkpoint_percent must be 50",
        f"{doc.relative}: live_evaluation_admission_percent was removed; only hard_checkpoint_percent is allowed",
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


def _handoff_body() -> str:
    return """# AR-119 active recovery capsule

## Checkpoint

Current checkpoint.

## Completed evidence

Current evidence.

## Exact blocker

Current blocker.

## Same-task continuity

Continue in the current task after a clean checkpoint.

## Next bounded work package

One package.

## Verification

Run checks.

## Constraints

Keep boundaries.
"""


def test_handoff_validation_accepts_one_bounded_capsule_per_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    issue = _document(
        _base_meta(
            type="issue",
            status="in_progress",
            epic="routing",
            issue_id="AR-119",
            priority="p0",
            tracker_url="https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132",
            depends_on=[],
            blocks=[],
        ),
        relative="docs/roadmap/issue-AR-119-fixture.md",
    )
    capsule_path = tmp_path / "docs/roadmap/handoffs/issue-AR-119.md"
    capsule_path.parent.mkdir(parents=True)
    capsule_path.write_text(_handoff_body(), encoding="utf-8")
    capsule = verify_docs.Document(
        path=capsule_path,
        meta=_base_meta(
            type="handoff",
            issue_id="AR-119",
            branch="codex/ar-119",
            evidence_commit="a" * 40,
            hard_checkpoint_percent=50,
            minimum_ledger_commit="b" * 40,
            tracker_url="https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132",
            related=[issue.relative],
        ),
        body=_handoff_body(),
    )
    errors: list[str] = []

    verify_docs.validate_handoffs([issue, capsule], errors)

    assert errors == []


def test_handoff_validation_rejects_duplicate_capsules_and_missing_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    issue = _document(
        _base_meta(
            type="issue",
            status="in_progress",
            epic="routing",
            issue_id="AR-119",
            priority="p0",
            tracker_url=None,
            depends_on=[],
            blocks=[],
        ),
        relative="docs/roadmap/issue-AR-119-fixture.md",
    )
    capsules: list[verify_docs.Document] = []
    for suffix in ("", "-duplicate"):
        path = tmp_path / f"docs/roadmap/handoffs/issue-AR-119{suffix}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Capsule\n", encoding="utf-8")
        capsules.append(
            verify_docs.Document(
                path=path,
                meta=_base_meta(
                    type="handoff",
                    issue_id="AR-119",
                    branch="codex/ar-119",
                    evidence_commit="a" * 40,
                    hard_checkpoint_percent=50,
                    minimum_ledger_commit="b" * 40,
                    tracker_url=None,
                    related=[issue.relative],
                ),
                body="# Capsule",
            )
        )
    errors: list[str] = []

    verify_docs.validate_handoffs([issue, *capsules], errors)

    assert "docs/roadmap/handoffs: multiple active capsules for AR-119" in errors
    assert any("missing handoff sections" in error for error in errors)


def test_handoff_validation_rejects_size_line_and_tracker_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    issue = _document(
        _base_meta(
            type="issue",
            status="in_progress",
            epic="routing",
            issue_id="AR-119",
            priority="p0",
            tracker_url=None,
            depends_on=[],
            blocks=[],
        ),
        relative="docs/roadmap/issue-AR-119-fixture.md",
    )
    capsule_path = tmp_path / "docs/roadmap/handoffs/issue-AR-119.md"
    capsule_path.parent.mkdir(parents=True)
    oversized = (
        _handoff_body()
        + ("extra line\n" * (verify_docs.HANDOFF_MAX_LINES + 1))
        + ("x" * verify_docs.HANDOFF_MAX_BYTES)
    )
    capsule_path.write_text(oversized, encoding="utf-8")
    capsule = verify_docs.Document(
        path=capsule_path,
        meta=_base_meta(
            type="handoff",
            issue_id="AR-119",
            branch="codex/ar-119",
            evidence_commit="a" * 40,
            hard_checkpoint_percent=50,
            minimum_ledger_commit="b" * 40,
            tracker_url="https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132",
            related=[issue.relative],
        ),
        body=_handoff_body(),
    )
    errors: list[str] = []

    verify_docs.validate_handoffs([issue, capsule], errors)

    assert any("maximum is 12288" in error for error in errors)
    assert any("maximum is 180" in error for error in errors)
    assert (f"{capsule.relative}: tracker_url must match {issue.relative}") in errors


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


def test_worklog_grandfathering_is_exact_and_future_mixed_ledgers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grandfathered = next(iter(verify_docs.GRANDFATHERED_LEDGER_COMMITS))
    future_mixed = "f" * 40

    def fake_git(*args: str) -> str:
        if args[0] == "log" and "--reverse" in args:
            return ""
        if args[0] == "log":
            return "\n".join(
                [
                    f"{grandfathered}\tdocs(worklog): historical exception",
                    f"{future_mixed}\tdocs(worklog): future mixed ledger",
                ]
            )
        assert args[0] == "diff-tree"
        assert args[-1] == future_mixed
        return "docs/worklog/README.md\ndocs/roadmap/issue-AR-999-example.md"

    monkeypatch.setattr(verify_docs, "git", fake_git)
    registry = _document(_base_meta(), relative="docs/worklog/README.md")
    errors: list[str] = []

    verify_docs.validate_worklog([registry], errors)

    assert errors == [
        "worklog ledger commit fffffff changes disallowed paths: "
        "docs/roadmap/issue-AR-999-example.md"
    ]


def test_worklog_short_shas_are_clone_independent_and_collision_checked() -> None:
    assert stable_short_shas(["a" * 40, "b" * 40]) == ["a" * 8, "b" * 8]
    with pytest.raises(ValueError, match="prefix collision"):
        stable_short_shas(["12345678" + "a" * 32, "12345678" + "b" * 32])
    with pytest.raises(ValueError, match="full lowercase Git SHAs"):
        stable_short_shas(["abc1234"])
