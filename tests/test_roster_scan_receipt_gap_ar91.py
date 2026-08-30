"""Fail-closed coverage for missing manifest source-scan receipts."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands
from agency_runtime.core.roster import lifecycle
from agency_runtime.core.roster.ingress import RosterSyncError


def test_cli_manifest_policy_rejects_missing_source_scan_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        roster_commands,
        "quarantine_manifest_import",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        roster_commands,
        "audit_candidates_with_policy",
        lambda *_args, **_kwargs: [],
    )

    with pytest.raises(RosterSyncError, match="one source scan receipt"):
        roster_commands._quarantine_manifest_with_policy(
            [],
            [],
            "source-id",
            object(),
            SimpleNamespace(required=False),
        )


def test_upstream_import_rejects_missing_source_scan_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = SimpleNamespace(
        agents=[],
        outcomes=[],
        public_dict=lambda: {},
    )
    policy = SimpleNamespace(
        required=False,
        public_dict=lambda: {"required": False},
    )
    monkeypatch.setattr(lifecycle, "inspect_upstream_source", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(lifecycle, "resolve_inference_audit_policy", lambda _config: policy)
    monkeypatch.setattr(
        lifecycle,
        "quarantine_manifest_import",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        lifecycle,
        "audit_candidates_with_policy",
        lambda *_args, **_kwargs: [],
    )

    with pytest.raises(RosterSyncError, match="one source scan receipt"):
        lifecycle.import_upstream_source(
            object(),  # type: ignore[arg-type]
            config=object(),  # type: ignore[arg-type]
            source_id="source-id",
            source_url="fixture://source",
        )
