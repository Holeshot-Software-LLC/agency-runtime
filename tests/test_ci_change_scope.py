from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import check_ci_whitespace
from scripts import classify_ci_change as subject


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "--initial-branch=main")
    _git(root, "config", "user.email", "ci@example.invalid")
    _git(root, "config", "user.name", "CI Contract")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("base\n", encoding="utf-8")
    (root / "source.py").write_text("BASE = True\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    return root, _git(root, "rev-parse", "HEAD")


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def test_docs_markdown_only_delta_skips_code_fanout(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    (root / "docs" / "guide.md").write_text("updated\n", encoding="utf-8")
    nested = root / "docs" / "roadmap"
    nested.mkdir()
    (nested / "issue.md").write_text("new\n", encoding="utf-8")
    head = _commit(root, "docs")

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (False, "docs_markdown_only")


@pytest.mark.parametrize(
    "relative_path",
    (
        "source.py",
        "README.md",
        "docs/generated.json",
        ".github/workflows/ci.yml",
        "scripts/check_ci_whitespace.py",
        "scripts/classify_ci_change.py",
    ),
)
def test_every_non_docs_markdown_path_requires_full_verification(
    tmp_path: Path,
    relative_path: str,
) -> None:
    root, base = _repository(tmp_path)
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n", encoding="utf-8")
    head = _commit(root, "non-docs")

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (True, "code_or_governance_change")


def test_rename_from_code_into_docs_fails_closed(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    (root / "source.py").rename(root / "docs" / "renamed.md")
    head = _commit(root, "rename")

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (True, "code_or_governance_change")


def test_empty_delta_and_non_pull_request_events_require_full_verification(
    tmp_path: Path,
) -> None:
    root, head = _repository(tmp_path)
    assert subject.classify_change(
        event_name="pull_request",
        base_sha=head,
        head_sha=head,
        root=root,
    ) == (True, "empty_delta_requires_full_verification")
    assert subject.classify_change(event_name="push") == (
        True,
        "event_requires_full_verification",
    )
    assert subject.classify_change(event_name="workflow_dispatch") == (
        True,
        "event_requires_full_verification",
    )


@pytest.mark.parametrize(
    ("event_name", "base_sha", "head_sha"),
    (
        ("schedule", "", ""),
        ("pull_request", "not-a-sha", "0" * 40),
        ("pull_request", "0" * 40, "not-a-sha"),
    ),
)
def test_invalid_events_and_commit_identities_fail_closed(
    tmp_path: Path,
    event_name: str,
    base_sha: str,
    head_sha: str,
) -> None:
    root, _head = _repository(tmp_path)
    with pytest.raises((RuntimeError, ValueError)):
        subject.classify_change(
            event_name=event_name,
            base_sha=base_sha,
            head_sha=head_sha,
            root=root,
        )


def test_merge_checkout_classifies_the_exact_event_commits(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    (root / "docs" / "guide.md").write_text("updated\n", encoding="utf-8")
    head = _commit(root, "docs")
    _git(root, "checkout", "--detach", base)
    _git(root, "merge", "--no-ff", "--no-edit", head)
    assert _git(root, "rev-parse", "HEAD") != head

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (False, "docs_markdown_only")


def test_non_regular_docs_markdown_entries_require_full_verification(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    _git(root, "update-index", "--chmod=+x", "docs/guide.md")
    _git(root, "commit", "-m", "executable docs")
    head = _git(root, "rev-parse", "HEAD")

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (True, "code_or_governance_change")


def test_docs_markdown_symlink_requires_full_verification(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    payload = root / "link-payload"
    payload.write_text("../source.py", encoding="utf-8")
    blob = _git(root, "hash-object", "-w", "link-payload")
    _git(
        root,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{blob},docs/link.md",
    )
    _git(root, "commit", "-m", "symlink docs")
    head = _git(root, "rev-parse", "HEAD")

    assert subject.classify_change(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    ) == (True, "code_or_governance_change")


def test_whitespace_check_uses_exact_pr_push_and_manual_ranges(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    (root / "docs" / "guide.md").write_text("clean\n", encoding="utf-8")
    head = _commit(root, "clean")

    assert (
        check_ci_whitespace.whitespace_comparison(
            event_name="pull_request",
            base_sha=base,
            head_sha=head,
            root=root,
        )
        == f"{base}...{head}"
    )
    assert (
        check_ci_whitespace.whitespace_comparison(
            event_name="push",
            before_sha=base,
            head_sha=head,
            root=root,
        )
        == f"{base}..{head}"
    )
    assert (
        check_ci_whitespace.whitespace_comparison(
            event_name="push",
            before_sha="0" * 40,
            head_sha=head,
            root=root,
        )
        == f"{check_ci_whitespace.EMPTY_TREE_SHA}..{head}"
    )
    assert (
        check_ci_whitespace.whitespace_comparison(
            event_name="workflow_dispatch",
            head_sha=head,
            root=root,
        )
        == f"{check_ci_whitespace.EMPTY_TREE_SHA}..{head}"
    )


def test_whitespace_check_reports_committed_pr_errors(tmp_path: Path) -> None:
    root, base = _repository(tmp_path)
    (root / "docs" / "guide.md").write_text("trailing  \n", encoding="utf-8")
    head = _commit(root, "whitespace")

    diagnostics = check_ci_whitespace.check_whitespace(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    )
    assert b"trailing whitespace" in diagnostics
    assert b"docs/guide.md" in diagnostics


def test_whitespace_cli_does_not_reflect_hostile_diagnostics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = _repository(tmp_path)
    target = root / "docs" / "workflow-command.md"
    target.write_text("::add-mask::ci-log-secret  \n", encoding="utf-8")
    head = _commit(root, "hostile whitespace")

    diagnostics = check_ci_whitespace.check_whitespace(
        event_name="pull_request",
        base_sha=base,
        head_sha=head,
        root=root,
    )
    assert b"ci-log-secret" in diagnostics
    assert b"docs/workflow-command.md" in diagnostics

    assert (
        check_ci_whitespace.main(
            [
                "--event",
                "pull_request",
                "--base-sha",
                base,
                "--head-sha",
                head,
                "--root",
                str(root),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Committed whitespace check failed.\n"
    assert "ci-log-secret" not in captured.err
    assert "add-mask" not in captured.err
    assert "workflow-command.md" not in captured.err


def test_cli_appends_only_bounded_governed_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "github-output"
    monkeypatch.setattr(
        subject,
        "classify_change",
        lambda **_kwargs: (False, "docs_markdown_only"),
    )

    assert (
        subject.main(
            [
                "--event",
                "pull_request",
                "--base-sha",
                "a" * 40,
                "--head-sha",
                "b" * 40,
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert output.read_text("utf-8") == ("code_required=false\nscope_reason=docs_markdown_only\n")
