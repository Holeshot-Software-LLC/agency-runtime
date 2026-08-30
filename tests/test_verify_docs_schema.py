"""Focused contracts for documentation front-matter schema variants."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts import update_worklog, verify_docs
from scripts.worklog_history import stable_short_shas


@pytest.fixture(autouse=True)
def _isolate_done_acceptance_exception_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep fixture-only document sets independent from repository exceptions."""

    monkeypatch.setattr(verify_docs, "DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS", {})


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


def test_documentation_git_subjects_are_decoded_as_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, object]] = []

    def fake_run(*args: object, **kwargs: object) -> object:
        captured.append(kwargs)
        return type(
            "Completed",
            (),
            {
                "stdout": (
                    f"{'a' * 40}\x1f2026-08-04\x1fAR-233: Architecture fixes — honest headers\n"
                )
            },
        )()

    monkeypatch.setattr(update_worklog.subprocess, "run", fake_run)

    assert update_worklog.git_log() == [
        ("aaaaaaaa", "2026-08-04", "AR-233: Architecture fixes — honest headers")
    ]
    assert verify_docs.git("log") == (
        f"{'a' * 40}\x1f2026-08-04\x1fAR-233: Architecture fixes — honest headers"
    )
    assert [invocation["encoding"] for invocation in captured] == ["utf-8", "utf-8"]


def _issue_with_acceptance(
    body: str,
    *,
    status: str = "done",
    relative: str = "docs/roadmap/issue-AR-999-fixture.md",
    superseded_by: str | None = None,
) -> verify_docs.Document:
    doc = _document(
        _base_meta(
            type="issue",
            status=status,
            epic="testing",
            issue_id="AR-999",
            priority="p1",
            tracker_url=None,
            depends_on=[],
            blocks=[],
            superseded_by=superseded_by,
        ),
        relative=relative,
    )
    doc.body = body
    return doc


def test_done_issue_acceptance_requires_real_checked_tasks() -> None:
    checked = _issue_with_acceptance("# Issue\n\n## Acceptance\n\n- [x] Proven.\n")
    open_issue = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n- [ ] Pending.\n", status="open"
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([checked, open_issue], errors)

    assert errors == []


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "# Issue\n",
            "requires exactly one real ## Acceptance section; found 0",
        ),
        ("# Issue\n\n## Acceptance\n\nNo tasks.\n", "Acceptance has no task markers"),
        (
            "# Issue\n\n```md\n## Acceptance\n- [x] Fake.\n```\n",
            "requires exactly one real ## Acceptance section; found 0",
        ),
        (
            "# Issue\n\n## Acceptance\n\n```md\n- [x] Fake.\n```\n- [ ] Real.\n",
            "has 1 unchecked Acceptance task(s)",
        ),
    ],
)
def test_done_issue_acceptance_rejects_missing_unchecked_and_fenced_bypasses(
    body: str,
    message: str,
) -> None:
    doc = _issue_with_acceptance(body)
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == [f"{doc.relative}: done issue {message}"]


def test_done_issue_acceptance_rejects_duplicate_sections_and_indented_fake_fence() -> None:
    duplicate = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n- [x] First.\n\n## Acceptance\n\n- [ ] Hidden second.\n"
    )
    indented = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n    ~~~\n- [ ] Not fenced.\n    ~~~\n"
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([duplicate, indented], errors)

    assert errors == [
        f"{duplicate.relative}: done issue requires exactly one real ## Acceptance "
        "section; found 2",
        f"{indented.relative}: done issue has 1 unchecked Acceptance task(s)",
    ]


def test_done_issue_acceptance_does_not_honor_invalid_backtick_info_fence() -> None:
    doc = _issue_with_acceptance("# Issue\n\n## Acceptance\n\n```bad`info\n- [ ] Real.\n```\n")
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == [f"{doc.relative}: done issue has 1 unchecked Acceptance task(s)"]


def test_done_issue_acceptance_rejects_indented_or_commented_fake_tasks() -> None:
    indented = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n    - [x] Indented code.\n",
        relative="docs/roadmap/issue-AR-998-indented.md",
    )
    commented = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n<!--\n- [x] Commented.\n-->\n",
        relative="docs/roadmap/issue-AR-999-commented.md",
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([indented, commented], errors)

    assert errors == [
        f"{indented.relative}: done issue has 1 unchecked Acceptance task(s)",
        f"{commented.relative}: done issue Acceptance has no task markers",
    ]


def test_done_issue_acceptance_detects_deep_nested_gfm_tasks() -> None:
    doc = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n"
        "- [x] Parent.\n"
        "  - [x] Child.\n"
        "    - [ ] Deep unfinished task.\n"
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == [f"{doc.relative}: done issue has 1 unchecked Acceptance task(s)"]


@pytest.mark.parametrize(
    "quoted_task",
    [
        "> - [ ] Blockquoted pending task.",
        "> - [x] Blockquoted checked example.",
        "> > 1. [ ] Nested quoted pending task.",
        "    > - [ ] Indented quoted pending task.",
        "1. > - [ ] Ordered-list quoted pending task.",
        "- > - [ ] Unordered-list quoted pending task.",
    ],
)
def test_done_issue_acceptance_rejects_blockquoted_task_markers(
    quoted_task: str,
) -> None:
    doc = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n- [x] Real completion.\n" + quoted_task + "\n"
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == [
        f"{doc.relative}: done issue Acceptance contains 1 blockquoted task marker(s); "
        "quoted examples cannot satisfy acceptance"
    ]


def test_done_issue_acceptance_allows_plain_blockquote_without_task_marker() -> None:
    doc = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n- [x] Real completion.\n"
        "> Historical prose without a checkbox.\n"
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == []


def test_done_issue_historical_exception_is_digest_and_successor_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "docs/roadmap/issue-AR-999-fixture.md"
    successor = "docs/roadmap/issue-AR-1000-successor.md"
    section = "## Acceptance\n\n- [x] Preserved.\n- [ ] Retired.\n"
    digest = hashlib.sha256(section.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        verify_docs,
        "DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS",
        {
            relative: {
                "acceptance_sha256": digest,
                "superseded_by": successor,
                "provenance_commit": "a" * 40,
                "reason": "retired surface",
            }
        },
    )
    historical_text = "---\ntitle: Historical\nstatus: done\n---\n\n# Issue\n\n" + section
    monkeypatch.setattr(verify_docs, "git", lambda *_args: historical_text)
    doc = _issue_with_acceptance(
        f"# Issue\n\n{section}", relative=relative, superseded_by=successor
    )
    successor_doc = _issue_with_acceptance(
        "# Successor\n\n## Acceptance\n\n- [ ] Open.\n",
        status="open",
        relative=successor,
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc, successor_doc], errors)

    assert errors == []

    doc.body = doc.body.replace("Retired.", "Changed.")
    verify_docs.validate_issue_acceptance([doc, successor_doc], errors)
    assert errors == [
        f"{relative}: historical Acceptance digest changed "
        f"(expected {digest}, got "
        f"{hashlib.sha256(section.replace('Retired.', 'Changed.').encode('utf-8')).hexdigest()})"
    ]


def test_unlisted_superseded_done_issue_cannot_bypass_acceptance() -> None:
    doc = _issue_with_acceptance(
        "# Issue\n\n## Acceptance\n\n- [ ] Pending.\n",
        superseded_by="docs/roadmap/issue-AR-1000-successor.md",
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc], errors)

    assert errors == [f"{doc.relative}: done issue has 1 unchecked Acceptance task(s)"]


def test_done_issue_historical_exception_rejects_malformed_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "docs/roadmap/issue-AR-999-fixture.md"
    successor = "docs/roadmap/issue-AR-1000-successor.md"
    section = "## Acceptance\n\n- [ ] Retired.\n"
    monkeypatch.setattr(
        verify_docs,
        "DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS",
        {
            relative: {
                "acceptance_sha256": hashlib.sha256(section.encode("utf-8")).hexdigest(),
                "superseded_by": successor,
                "provenance_commit": "not-a-commit",
                "reason": "",
            }
        },
    )
    doc = _issue_with_acceptance(
        f"# Issue\n\n{section}", relative=relative, superseded_by=successor
    )
    successor_doc = _issue_with_acceptance(
        "# Successor\n\n## Acceptance\n\n- [ ] Open.\n",
        status="open",
        relative=successor,
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([doc, successor_doc], errors)

    assert errors == [
        f"{relative}: historical Acceptance exception needs a full provenance commit",
        f"{relative}: historical Acceptance exception needs a non-empty reason",
    ]


def test_done_issue_historical_exception_requires_existing_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative = "docs/roadmap/issue-AR-999-missing.md"
    monkeypatch.setattr(
        verify_docs,
        "DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS",
        {
            relative: {
                "acceptance_sha256": "a" * 64,
                "superseded_by": "docs/roadmap/issue-AR-1000-successor.md",
                "provenance_commit": "b" * 40,
                "reason": "retired",
            }
        },
    )
    errors: list[str] = []

    verify_docs.validate_issue_acceptance([], errors)

    assert errors == [f"{relative}: configured done-acceptance exception document is missing"]


def _ar119_authority_docs(
    tmp_path: Path,
    *,
    vision_body: str = "## Canonical card metaphor\nCanonical.\n\n## Differentiator\nNovel.\n",
) -> tuple[verify_docs.Document, verify_docs.Document]:
    block = verify_docs._canonical_vision_block(vision_body)
    assert block is not None
    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
    vision = _document(
        _base_meta(
            ar119_authority="vision-wording",
            canonical_block_sha256=digest,
        ),
        relative=verify_docs.AR119_AUTHORITY_PATHS["vision-wording"],
    )
    vision.body = vision_body
    header = "| " + " | ".join(verify_docs.AR119_MATRIX_COLUMNS) + " |"
    separator = "|" + "|".join("---" for _ in verify_docs.AR119_MATRIX_COLUMNS) + "|"
    rows = [
        "| "
        + " | ".join(
            [
                rule,
                host,
                "unproven",
                "unproven",
                "unproven",
                "unproven",
                "unproven",
                "required artifact",
                "none",
                "unobserved",
                "fixture source",
                "missing evidence",
            ]
        )
        + " |"
        for rule in sorted(verify_docs.AR119_RULES, key=lambda value: int(value[1:]))
        for host in sorted(verify_docs.AR119_SUPPORTED_HOSTS)
    ]
    matrix = _document(
        _base_meta(
            ar119_authority="completion-evidence",
            vision_block_sha256=digest,
            candidate_commit="a" * 40,
            evidence_cutoff="2026-07-12",
        ),
        relative=verify_docs.AR119_AUTHORITY_PATHS["completion-evidence"],
    )
    layer_header = "| " + " | ".join(verify_docs.AR119_LAYER_EVIDENCE_COLUMNS) + " |"
    layer_separator = "|" + "|".join("---" for _ in verify_docs.AR119_LAYER_EVIDENCE_COLUMNS) + "|"
    matrix.body = (
        "# Matrix\n\n## Canonical matrix\n\n"
        + header
        + "\n"
        + separator
        + "\n"
        + "\n".join(rows)
        + "\n\n## Layer evidence\n\n"
        + layer_header
        + "\n"
        + layer_separator
        + "\n"
    )
    return vision, matrix


def test_ar119_authorities_accept_exact_digest_matrix_and_crlf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(
        tmp_path,
        vision_body=(
            "## Canonical card metaphor\r\nCanonical.\r\n\r\n## Differentiator\r\nNovel.\r\n"
        ),
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert errors == []


def test_ar119_authorities_reject_vision_tamper_and_bad_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    vision.body = vision.body.replace("Canonical.", "Tampered.")
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("canonical vision digest mismatch" in error for error in errors)

    vision.body = "## Differentiator\nFirst.\n## Canonical card metaphor\nSecond.\n"
    errors = []
    verify_docs.validate_ar119_authorities([vision, matrix], errors)
    assert any("canonical vision boundaries are missing or ambiguous" in error for error in errors)


def test_ar119_authorities_reject_fenced_canonical_vision_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    vision.body = "```md\n" + vision.body + "```\n\n# Visible replacement\n"
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("canonical vision boundaries are missing or ambiguous" in error for error in errors)


@pytest.mark.parametrize(
    "wrapper",
    [
        ("<details><summary>Archived</summary>\n", "\n</details>"),
        (
            "<details><!--x-->\n<summary><!--x-->hidden</summary>\n",
            "\n</details><!--x-->",
        ),
        ('<DIV hidden\nclass="archived">\n', "\n</DIV>"),
        ("<template>\n", "\n</template>"),
    ],
)
def test_ar119_authorities_reject_canonical_vision_inside_raw_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrapper: tuple[str, str],
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    prefix, suffix = wrapper
    vision.body = (
        "## Canonical card metaphor\nVisible replacement.\n\n## Differentiator\n"
        "Visible replacement.\n\n"
        + prefix
        + "## Canonical card metaphor\nCanonical.\n\n## Differentiator\nNovel."
        + suffix
        + "\n"
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("canonical vision boundaries are missing or ambiguous" in error for error in errors)


def test_ar119_authority_allows_raw_html_literal_inside_fenced_example(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(
        tmp_path,
        vision_body=(
            "```html\n<details>example only</details>\n```\n\n"
            "## Canonical card metaphor\nCanonical.\n\n## Differentiator\nNovel.\n"
        ),
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert errors == []


def test_ar119_authorities_reject_duplicate_wrong_path_and_unknown_role(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    duplicate = _document(
        _base_meta(ar119_authority="vision-wording"),
        relative="docs/roadmap/duplicate.md",
    )
    unknown = _document(
        _base_meta(ar119_authority="everything"),
        relative="docs/roadmap/unknown.md",
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix, duplicate, unknown], errors)

    assert any("reserved for docs/roadmap/AR-119-founding-vision.md" in error for error in errors)
    assert any("requires exactly one document" in error and "found 2" in error for error in errors)
    assert any("unknown ar119_authority role 'everything'" in error for error in errors)


def test_ar119_matrix_rejects_missing_duplicate_and_invalid_cells(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    missing_row = next(
        line for line in matrix.body.splitlines() if line.startswith("| R1 | claude |")
    )
    duplicate_row = next(
        line for line in matrix.body.splitlines() if line.startswith("| R1 | codex |")
    )
    matrix.body = matrix.body.replace(missing_row + "\n", "", 1)
    matrix.body = matrix.body.replace(
        "\n\n## Layer evidence", "\n" + duplicate_row + "\n\n## Layer evidence", 1
    )
    matrix.body = matrix.body.replace("| R2 | codex | unproven |", "| R2 | codex | invalid |", 1)
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("duplicate matrix cell R1/codex" in error for error in errors)
    assert any("matrix is missing cells R1/claude" in error for error in errors)
    assert any("R2/codex has invalid State state 'invalid'" in error for error in errors)


def test_ar119_matrix_rejects_false_green_rule_nine_and_missing_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body = matrix.body.replace(
        "| R1 | claude | unproven | unproven | unproven | unproven | unproven |",
        "| R1 | claude | proven | negative | unproven | unproven | unproven |",
        1,
    )
    matrix.body = matrix.body.replace(
        "| R9 | claude | unproven | unproven | unproven | unproven | unproven |",
        "| R9 | claude | proven | proven | proven | proven | proven |",
        1,
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("R1/claude State must derive" in error for error in errors)
    assert any("R1/claude asserted evidence needs an artifact" in error for error in errors)
    assert any("R1/claude asserted evidence needs an observation date" in error for error in errors)
    assert any("R9/claude State must derive from R1-R8" in error for error in errors)


def test_ar119_matrix_rejects_fenced_table_invalid_candidate_and_cutoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.meta["candidate_commit"] = "garbage"
    matrix.meta["evidence_cutoff"] = "not-a-date"
    matrix.body = matrix.body.replace("## Canonical matrix\n\n", "## Canonical matrix\n\n````md\n")
    matrix.body += "\n```\n````\n"
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("candidate_commit must be a full lowercase Git SHA" in error for error in errors)
    assert any("evidence_cutoff must be YYYY-MM-DD" in error for error in errors)
    assert any("missing or malformed canonical evidence matrix table" in error for error in errors)


@pytest.mark.parametrize(
    "wrapper",
    [
        ("<!--\n", "\n-->"),
        ("    ", ""),
    ],
)
def test_ar119_matrix_rejects_commented_or_indented_authority_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrapper: tuple[str, str],
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "")
    vision, matrix = _ar119_authority_docs(tmp_path)
    prefix, suffix = wrapper
    heading, table = matrix.body.split("## Canonical matrix\n\n", 1)
    if prefix == "    ":
        table = "\n".join(prefix + line for line in table.splitlines())
        matrix.body = heading + "## Canonical matrix\n\n" + table
    else:
        matrix.body = heading + "## Canonical matrix\n\n" + prefix + table + suffix
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("missing or malformed canonical evidence matrix table" in error for error in errors)


def test_ar119_matrix_rejects_missing_candidate_and_post_cutoff_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)

    def missing_commit(*_args: str) -> str:
        raise verify_docs.subprocess.CalledProcessError(1, ["git", "cat-file"])

    monkeypatch.setattr(verify_docs, "git", missing_commit)
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body = matrix.body.replace(
        "| R1 | claude | unproven | unproven | unproven | unproven | unproven "
        "| required artifact | none | unobserved |",
        "| R1 | claude | unproven | unproven | unproven | unproven | unproven "
        "| required artifact | none | 2026-07-13 |",
        1,
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("candidate_commit does not identify a Git commit" in error for error in errors)
    assert any("R1/claude observation exceeds evidence_cutoff" in error for error in errors)


def test_ar119_matrix_rejects_non_ancestor_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)

    def non_ancestor(*args: str) -> str:
        if args[0] == "merge-base":
            raise verify_docs.subprocess.CalledProcessError(1, ["git", *args])
        return ""

    monkeypatch.setattr(verify_docs, "git", non_ancestor)
    vision, matrix = _ar119_authority_docs(tmp_path)
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("candidate_commit must be an ancestor of HEAD" in error for error in errors)


def test_ar119_matrix_requires_scope_bound_layer_evidence_for_each_assertion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "line\n")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body = matrix.body.replace(
        "| R2 | claude | unproven | unproven | unproven | unproven | unproven "
        "| required artifact | none | unobserved | fixture source | missing evidence |",
        "| R2 | claude | unproven | proven | unproven | unproven | unproven "
        "| unsupported assertion | README.md | 2026-07-12 | README.md | claimed |",
        1,
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("missing layer evidence R2/claude/Implementation" in error for error in errors)


def test_ar119_matrix_accepts_exact_typed_candidate_bound_layer_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "line\n")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body = matrix.body.replace(
        "| R2 | claude | unproven | unproven | unproven | unproven | unproven "
        "| required artifact | none | unobserved | fixture source | missing evidence |",
        "| R2 | claude | unproven | proven | unproven | unproven | unproven "
        "| source-bound proof | exact source receipt | 2026-07-12 "
        "| `agency_runtime/fixture.py:1` | installed and live remain unproven |",
        1,
    )
    matrix.body += (
        "| R2 | claude | Implementation | proven | source | exact source receipt "
        "| 2026-07-12 | `agency_runtime/fixture.py:1` |\n"
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert errors == []


def test_ar119_layer_evidence_rejects_wrong_kind_bare_source_and_r9_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "line\n")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body += (
        "| R9 | claude | Implementation | negative | live-host | aggregate | 2026-07-12 "
        "| README.md |\n"
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any("R9 must not have direct layer evidence" in error for error in errors)
    assert any("supplies evidence for an unasserted layer" in error for error in errors)
    assert any("Authority kind must be 'source'" in error for error in errors)
    assert any("Source must be an exact repository" in error for error in errors)


def test_ar119_layer_evidence_rejects_unrelated_source_authority_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verify_docs, "ROOT", tmp_path)
    monkeypatch.setattr(verify_docs, "git", lambda *_args: "line\n")
    vision, matrix = _ar119_authority_docs(tmp_path)
    matrix.body = matrix.body.replace(
        "| R2 | claude | unproven | unproven | unproven | unproven | unproven "
        "| required artifact | none | unobserved | fixture source | missing evidence |",
        "| R2 | claude | unproven | proven | unproven | unproven | unproven "
        "| source proof | exact receipt | 2026-07-12 | `README.md:1` | partial |",
        1,
    )
    matrix.body += (
        "| R2 | claude | Implementation | proven | source | exact receipt "
        "| 2026-07-12 | `README.md:1` |\n"
    )
    errors: list[str] = []

    verify_docs.validate_ar119_authorities([vision, matrix], errors)

    assert any(
        "R2/claude/Implementation source authority must cite agency_runtime/" in error
        for error in errors
    )
