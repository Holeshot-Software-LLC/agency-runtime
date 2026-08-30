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
