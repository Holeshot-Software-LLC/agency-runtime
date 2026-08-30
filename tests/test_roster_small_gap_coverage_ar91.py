"""Focused fail-closed coverage for small roster integrity helpers."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.roster import revisions, source_safety


def _revision_metadata() -> dict[str, Any]:
    return revisions.revision_metadata(
        {
            "name": "Reviewer",
            "division": "engineering",
            "description": "Reviews changes",
            "source": "test",
            "prompt_path": "agents/reviewer.md",
            "source_version": "1.0.0",
            "categories": ["review"],
            "capabilities": ["analysis"],
            "tool_affinity": ["git"],
        }
    )


def test_revision_projection_accepts_scalar_list_shorthand() -> None:
    projected = revisions.revision_metadata(
        {
            "name": "Reviewer",
            "categories": "review",
            "capabilities": "analysis",
            "tool_affinity": "git",
        }
    )
    assert projected["categories"] == ["review"]
    assert projected["capabilities"] == ["analysis"]
    assert projected["tool_affinity"] == ["git"]


@pytest.mark.parametrize(
    "value",
    [
        "{",
        "[]",
        json.dumps({}),
        json.dumps({**_revision_metadata(), "name": 1}),
        json.dumps({**_revision_metadata(), "source_version": 1}),
        json.dumps({**_revision_metadata(), "categories": [1]}),
        json.dumps({**_revision_metadata(), "authority": 1}),
        json.dumps({**_revision_metadata(), "anti_capabilities": [1]}),
    ],
)
def test_revision_metadata_decoder_rejects_every_malformed_projection(value: str) -> None:
    assert revisions.decode_revision_metadata(value) is None


def test_source_safety_rejects_invalid_duplicate_and_oversized_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = source_safety.UnsafeSourceControl(0x41, (0,))
    with pytest.raises(ValueError, match="control evidence"):
        source_safety.format_unsafe_control_finding(
            source_safety.SourceSafetyScan((invalid,), False)
        )

    duplicate = source_safety.UnsafeSourceControl(0x202E, (0,))
    with pytest.raises(ValueError, match="unique and sorted"):
        source_safety.format_unsafe_control_finding(
            source_safety.SourceSafetyScan((duplicate, duplicate), False)
        )

    monkeypatch.setattr(source_safety, "_MAX_FINDING_BYTES", 1)
    with pytest.raises(ValueError, match="byte limit"):
        source_safety.format_unsafe_control_finding(source_safety.scan_source_text("\u202e"))
