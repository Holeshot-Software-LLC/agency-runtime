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


def test_tracker_verifier_matches_both_bracketed_and_colon_title_styles(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """AR-347: 'AR-NNN: Title' trackers must match, not read as missing_remote."""

    verifier = _load_verifier()
    for issue_id, name in (("AR-01", "bracketed"), ("AR-02", "colon")):
        (tmp_path / f"issue-{issue_id}-{name}.md").write_text(
            f"""---
issue_id: {issue_id}
status: open
epic: testing
tracker_url: https://example.test/issues/{issue_id[-1]}
---
""",
            encoding="utf-8",
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
            "title": "AR-99 no separator is not an ID match",
            "state": "OPEN",
            "url": "https://example.test/issues/3",
            "labels": [],
        },
    ]
    monkeypatch.setattr(verifier, "ROADMAP", tmp_path)
    monkeypatch.setattr(verifier, "gh", lambda *_args: remote)

    assert verifier.main([]) == 0
    output = capsys.readouterr()
    assert "tracker validation passed for 2 roadmap items" in output.out
    assert "missing_remote" not in output.err
