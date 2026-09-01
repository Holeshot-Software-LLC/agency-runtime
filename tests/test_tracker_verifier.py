"""Read-only tracker verifier behavior for authorization-pending closure."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_verifier():
    path = Path(__file__).parents[1] / "scripts" / "verify_tracker.py"
    spec = importlib.util.spec_from_file_location("verify_tracker_test_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tracker_verifier_keeps_strict_default_and_explicit_override(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    verifier = _load_verifier()
    issue = tmp_path / "issue-AR-01-test.md"
    issue.write_text(
        """---
issue_id: AR-01
status: done
epic: testing
tracker_url: https://example.test/issues/1
---
""",
        encoding="utf-8",
    )
    remote = [
        {
            "number": 1,
            "title": "[AR-01] Test",
            "state": "OPEN",
            "url": "https://example.test/issues/1",
            "labels": [{"name": "epic:testing"}],
        }
    ]
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: remote)

    assert verifier.main([]) == 1
    strict = capsys.readouterr()
    assert "tracker state OPEN != CLOSED" in strict.err

    assert verifier.main(["--allow-open-complete"]) == 0
    allowed = capsys.readouterr()
    assert "closure pending authorization" in allowed.err
    assert "tracker validation passed for 1 roadmap items" in allowed.out


@pytest.mark.parametrize("payload", [{}, ["not-an-object"]])
def test_tracker_verifier_rejects_malformed_remote_issue_collections(payload) -> None:
    verifier = _load_verifier()

    with pytest.raises(RuntimeError, match="tracker issue listing"):
        verifier._remote_issue_objects(payload)


def _write_issue(tmp_path, issue_id, name, tracker_url="null", status="open"):
    (tmp_path / f"issue-{issue_id}-{name}.md").write_text(
        f"""---
issue_id: {issue_id}
status: {status}
epic: testing
tracker_url: {tracker_url}
---
""",
        encoding="utf-8",
    )


def test_tracker_verifier_exempts_pre_tracker_history_from_missing_remote(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """AR-347: allow-listed pre-tracker docs do not fail the ID parity check."""

    verifier = _load_verifier()
    _write_issue(tmp_path, "AR-01", "historic")
    history = tmp_path / "pre-tracker-history.txt"
    history.write_text("# comment line\nAR-01\n", encoding="utf-8")
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: [])

    assert verifier.main([]) == 0
    output = capsys.readouterr()
    assert "tracker validation passed for 1 roadmap items" in output.out

    # Without the exemption the same layout fails the parity check.
    history.unlink()
    assert verifier.main([]) == 1
    assert "missing_remote=['AR-01']" in capsys.readouterr().err


def test_tracker_verifier_fails_on_stale_orphan_and_out_of_range_exemptions(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """AR-347: both gates share the allow-list entry rules; this gate enforces
    stale (doc now tracked), orphan (no doc), and out-of-range entries."""

    verifier = _load_verifier()
    _write_issue(tmp_path, "AR-01", "stale", tracker_url="https://example.test/issues/1")
    (tmp_path / "pre-tracker-history.txt").write_text("AR-01\nAR-02\nAR-999\n", encoding="utf-8")
    remote = [
        {
            "number": 1,
            "title": "[AR-01] Stale exemption",
            "state": "OPEN",
            "url": "https://example.test/issues/1",
            "labels": [{"name": "epic:testing"}],
        }
    ]
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: remote)

    assert verifier.main([]) == 1
    err = capsys.readouterr().err
    assert "entry AR-01 now carries a tracker URL" in err
    assert "entry AR-02 matches no roadmap issue doc" in err
    assert "entry AR-999 is outside pre-tracker history" in err


def test_tracker_verifier_skips_only_the_known_pr_tracked_history(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """AR-347: the PR-tracked carve-out is closed; other docs may not use it,
    and a PR-tracked duplicate still trips duplicate-ID detection."""

    verifier = _load_verifier()
    _write_issue(
        tmp_path,
        "AR-227",
        "pr-tracked",
        tracker_url="https://example.test/pull/236",
        status="done",
    )
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: [])

    assert verifier.main([]) == 0
    passed = capsys.readouterr()
    assert "tracker validation passed for 0 roadmap items" in passed.out
    assert "PR-tracked historical item(s) skipped" in passed.out

    # A non-historical doc may not opt out through a pull-request URL.
    _write_issue(
        tmp_path,
        "AR-05",
        "bogus-pr",
        tracker_url="https://example.test/pull/9999",
    )
    assert verifier.main([]) == 1
    assert "AR-05: tracker_url must reference an issue, not a pull request" in (
        capsys.readouterr().err
    )

    # Duplicate IDs are detected even when the first duplicate is PR-tracked.
    (tmp_path / "issue-AR-05-bogus-pr.md").unlink()
    _write_issue(
        tmp_path,
        "AR-227",
        "z-duplicate",
        tracker_url="https://example.test/issues/9",
    )
    assert verifier.main([]) == 1
    assert "duplicate local issue ID AR-227" in capsys.readouterr().err


def test_tracker_verifier_matches_all_recognized_title_styles(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """AR-347: bracketed, colon, and hybrid tracker titles must all match."""

    verifier = _load_verifier()
    for number, (issue_id, name) in enumerate(
        (("AR-01", "bracketed"), ("AR-02", "colon"), ("AR-03", "hybrid")),
        start=1,
    ):
        _write_issue(
            tmp_path,
            issue_id,
            name,
            tracker_url=f"https://example.test/issues/{number}",
        )
    remote = [
        {
            "number": 1,
            "title": "[AR-01] Bracketed style",
            "state": "OPEN",
            "url": "https://example.test/issues/1",
            "labels": [{"name": "epic:testing"}],
        },
        {
            "number": 2,
            "title": "AR-02: Colon style",
            "state": "OPEN",
            "url": "https://example.test/issues/2",
            "labels": [{"name": "epic:testing"}],
        },
        {
            "number": 3,
            "title": "[AR-03]: Hybrid style",
            "state": "OPEN",
            "url": "https://example.test/issues/3",
            "labels": [{"name": "epic:testing"}],
        },
        {
            "number": 4,
            "title": "AR-99 no separator is not an ID match",
            "state": "OPEN",
            "url": "https://example.test/issues/4",
            "labels": [],
        },
    ]
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: remote)

    assert verifier.main([]) == 0
    output = capsys.readouterr()
    assert "tracker validation passed for 3 roadmap items" in output.out
    assert "missing_remote" not in output.err
