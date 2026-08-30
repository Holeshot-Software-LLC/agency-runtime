"""Public roster activation and rollback-authority security contracts."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.roster import review as review_subject
from agency_runtime.core.roster import snapshot_authority as snapshot_authority_subject
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.review import (
    MAX_AUDIT_FINDINGS,
    MAX_INFERENCE_EVIDENCE_BYTES,
    assert_bound_candidate_audit_from_connection,
)
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.roster.snapshot_authority import (
    snapshot_authority_detail,
    validate_snapshot_authority_detail,
)
from agency_runtime.core.roster.sync import (
    RosterSyncError,
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    quarantine_candidate,
)
from agency_runtime.core.store import roster_authority as roster_authority_subject
from agency_runtime.core.store.roster_authority import (
    assert_active_revision_projection,
    assert_revision_activation_authority,
)
from agency_runtime.core.store.sqlite import Store


def _canonical(slug: str = "code-reviewer") -> dict[str, Any]:
    return next(agent for agent in bundled_roster() if agent["slug"] == slug)


def _governed_candidate(slug: str, prompt: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": f"Governed {slug} candidate.",
        "division": "engineering",
        "categories": ["engineering", "testing"],
        "capabilities": ["perform bounded fixture work"],
        "anti_capabilities": ["claim unverified completion"],
        "task_types": ["review"],
        "preferred_when": ["the bounded fixture matches"],
        "avoid_when": ["required evidence is unavailable"],
        "required_tools": [],
        "tool_affinity": [],
        "supported_hosts": ["codex"],
        "supported_platforms": ["linux", "windows"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": f"fixture-{slug}",
        "expected_output_contract": "Return bounded evidence-backed fixture output.",
        "evidence_requirements": ["cite the fixture result"],
        "model_requirements": ["instruction-adherence"],
        "source_revision": "test-revision",
        "audit_revision": "test",
        "audit_status": "approved",
        "findings": [],
        "prompt_body": prompt,
    }
    return {
        **payload,
        "content": json.dumps(payload, sort_keys=True, separators=(",", ":")),
    }


def _canonical_revision_projection() -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = _canonical()
    revision = {
        "agent_slug": canonical["slug"],
        "version": canonical["version"],
        "source_version": canonical["source_version"],
        "source_id": canonical["source_id"],
        "hash": canonical["hash"],
        "content": canonical["prompt_body"],
        "metadata": serialized_revision_metadata(canonical),
    }
    active = {
        "agent_slug": canonical["slug"],
        "name": canonical["name"],
        "division": canonical["division"],
        "description": canonical["description"],
        "source": canonical["source"],
        "source_id": canonical["source_id"],
        "source_version": canonical["source_version"],
        "version": canonical["version"],
        "hash": canonical["hash"],
        "categories": json.dumps(canonical["categories"]),
        "capabilities": json.dumps(canonical["capabilities"]),
        "tool_affinity": json.dumps(canonical["tool_affinity"]),
        "prompt_path": canonical["prompt_path"],
    }
    return active, revision


def _private_agent(
    slug: str,
    *,
    version: str,
    prompt: str,
) -> dict[str, object]:
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": f"Private fixture {slug}.",
        "division": "engineering",
        "categories": ["engineering"],
        "capabilities": ["fixture setup"],
        "tool_affinity": [],
        "version": version,
        "prompt_body": prompt,
    }


def _activate_candidate(
    store: Store,
    source_id: str,
    *,
    slug: str,
    prompt: str,
) -> tuple[dict[str, Any], str, str]:
    candidate_id = quarantine_candidate(
        _governed_candidate(slug, prompt),
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    snapshot_id = str(snapshot["snapshot_id"])
    approve_snapshot(store, snapshot_id)
    activate_snapshot(store, snapshot_id)
    active = store.get_roster_entry(slug)
    assert active is not None
    return active, snapshot_id, candidate_id


def _generation(store: Store) -> int:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
        assert row is not None
        return int(row["value"])
    finally:
        conn.close()


def _audit_binding(
    conn: Any,
    candidate_id: str,
) -> tuple[str, str, str]:
    candidate = conn.execute(
        "SELECT version, hash FROM agent_candidates WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    audit = conn.execute(
        "SELECT id FROM agent_candidate_audits WHERE candidate_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (candidate_id,),
    ).fetchone()
    assert candidate is not None
    assert audit is not None
    return str(audit["id"]), str(candidate["version"]), str(candidate["hash"])


def test_exact_active_projection_and_bundle_authority() -> None:
    active, revision = _canonical_revision_projection()

    assert assert_active_revision_projection(active, revision)["name"] == active["name"]
    authority = assert_revision_activation_authority(
        None,
        slug=active["agent_slug"],
        revision=revision,
    )
    assert authority.kind == "bundled"
    assert len(authority.digest) == 64
    assert dict(authority.projection).keys() == {"manifest_digest", "revision_digest"}


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("revision", "metadata", "{}", "predates"),
        ("revision", "source_version", "wrong", "metadata integrity"),
        ("revision", "content", "tampered", "revision integrity"),
        ("active", "description", "tampered", "active revision projection"),
        ("active", "categories", "", "active categories is invalid"),
        ("active", "categories", "{}", "active categories is invalid"),
        ("active", "categories", "[1]", "active categories is invalid"),
        ("active", "categories", "[]", "active revision projection"),
    ],
)
def test_active_projection_rejects_tampering(
    target: str,
    field: str,
    value: str,
    message: str,
) -> None:
    active, revision = _canonical_revision_projection()
    (active if target == "active" else revision)[field] = value

    with pytest.raises(ValueError, match=message):
        assert_active_revision_projection(active, revision)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", "1.0.0"),
        ("hash", "opaque"),
        ("content", ""),
    ],
)
def test_rollback_authority_rejects_non_immutable_target_shape(
    field: str,
    value: str,
) -> None:
    active, revision = _canonical_revision_projection()
    revision[field] = value
    with pytest.raises(ValueError, match="activation authority is invalid"):
        assert_revision_activation_authority(
            None,
            slug=active["agent_slug"],
            revision=revision,
        )


def test_snapshot_authority_receipt_is_canonical_and_manifest_bound() -> None:
    manifest = '{"approved":true,"candidates":[]}'
    audit_ids = {"candidate-1": "audit-" + ("a" * 64)}
    detail = snapshot_authority_detail(
        snapshot_id="snapshot-1",
        manifest_json=manifest,
        audit_ids=audit_ids,
    )

    assert (
        validate_snapshot_authority_detail(
            detail,
            snapshot_id="snapshot-1",
            manifest_json=manifest,
            candidate_ids=["candidate-1"],
        )
        == audit_ids
    )
    with pytest.raises(RosterSyncError, match="does not match"):
        validate_snapshot_authority_detail(
            detail,
            snapshot_id="snapshot-1",
            manifest_json=manifest + " ",
            candidate_ids=["candidate-1"],
        )
    with pytest.raises(RosterSyncError, match="candidate identities"):
        validate_snapshot_authority_detail(
            detail,
            snapshot_id="snapshot-1",
            manifest_json=manifest,
            candidate_ids=["candidate-2"],
        )
    with pytest.raises(RosterSyncError, match="canonical"):
        validate_snapshot_authority_detail(
            detail + " ",
            snapshot_id="snapshot-1",
            manifest_json=manifest,
            candidate_ids=["candidate-1"],
        )


@pytest.mark.parametrize(
    "audit_ids",
    [
        {"candidate-1": "not-an-audit"},
        {"": "audit-" + ("a" * 64)},
    ],
)
def test_snapshot_authority_receipt_rejects_invalid_audit_bindings(
    audit_ids: dict[str, str],
) -> None:
    with pytest.raises(RosterSyncError):
        snapshot_authority_detail(
            snapshot_id="snapshot-1",
            manifest_json="{}",
            audit_ids=audit_ids,
        )


@pytest.mark.parametrize("primitive", [None, True, 1, 1.5])
def test_snapshot_authority_receipt_rejects_non_text_identity_tokens(
    primitive: object,
) -> None:
    audit_id = "audit-" + ("a" * 64)
    with pytest.raises(RosterSyncError, match="must be text"):
        snapshot_authority_detail(
            snapshot_id=primitive,
            manifest_json="{}",
            audit_ids={},
        )
    with pytest.raises(RosterSyncError, match="must be text"):
        snapshot_authority_detail(
            snapshot_id="snapshot-1",
            manifest_json="{}",
            audit_ids={primitive: audit_id},  # type: ignore[dict-item]
        )
    detail = snapshot_authority_detail(
        snapshot_id="snapshot-1",
        manifest_json="{}",
        audit_ids={},
    )
    with pytest.raises(RosterSyncError, match="must be text"):
        validate_snapshot_authority_detail(
            detail,
            snapshot_id=primitive,
            manifest_json="{}",
            candidate_ids=[],
        )
    with pytest.raises(RosterSyncError, match="must be text"):
        validate_snapshot_authority_detail(
            detail,
            snapshot_id="snapshot-1",
            manifest_json="{}",
            candidate_ids=[primitive],  # type: ignore[list-item]
        )


def test_snapshot_authority_receipt_bounds_and_malformed_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_id = "audit-" + ("a" * 64)
    with pytest.raises(RosterSyncError, match="must be text"):
        snapshot_authority_subject.snapshot_manifest_hash(None)
    with pytest.raises(RosterSyncError, match="invalid or unbounded"):
        snapshot_authority_subject.snapshot_manifest_hash("")
    with pytest.raises(RosterSyncError, match="representation is invalid"):
        snapshot_authority_subject.snapshot_manifest_hash("\ud800")
    with pytest.raises(RosterSyncError, match="canonical text"):
        validate_snapshot_authority_detail(
            {},
            snapshot_id="snapshot-1",
            manifest_json="{}",
            candidate_ids=[],
        )
    with pytest.raises(RosterSyncError, match="receipt is invalid"):
        validate_snapshot_authority_detail(
            "{",
            snapshot_id="snapshot-1",
            manifest_json="{}",
            candidate_ids=[],
        )
    with pytest.raises(RosterSyncError, match="candidate identities are invalid"):
        validate_snapshot_authority_detail(
            snapshot_authority_detail(
                snapshot_id="snapshot-1",
                manifest_json="{}",
                audit_ids={"candidate-1": audit_id},
            ),
            snapshot_id="snapshot-1",
            manifest_json="{}",
            candidate_ids="candidate-1",  # type: ignore[arg-type]
        )
    with pytest.raises(RosterSyncError, match="candidate identities are invalid"):
        validate_snapshot_authority_detail(
            snapshot_authority_detail(
                snapshot_id="snapshot-1",
                manifest_json="{}",
                audit_ids={"candidate-1": audit_id},
            ),
            snapshot_id="snapshot-1",
            manifest_json="{}",
            candidate_ids={"candidate-1": audit_id},  # type: ignore[arg-type]
        )

    monkeypatch.setattr(snapshot_authority_subject, "MAX_SOURCE_CANDIDATES", 0)
    with pytest.raises(RosterSyncError, match="invalid or unbounded"):
        snapshot_authority_detail(
            snapshot_id="snapshot-1",
            manifest_json="{}",
            audit_ids={"candidate-1": audit_id},
        )
    monkeypatch.setattr(snapshot_authority_subject, "MAX_SOURCE_CANDIDATES", 1)
    monkeypatch.setattr(snapshot_authority_subject, "MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES", 1)
    with pytest.raises(RosterSyncError, match="exceeds its bound"):
        snapshot_authority_detail(
            snapshot_id="snapshot-1",
            manifest_json="{}",
            audit_ids={},
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("receipt_schema", "wrong", "does not match"),
        ("snapshot_id", "wrong", "does not match"),
        ("manifest_hash", "not-a-hash", "does not match"),
        ("audit_ids", [], "audit identities"),
    ],
)
def test_snapshot_authority_receipt_rejects_tampered_fields(
    field: str,
    value: object,
    message: str,
) -> None:
    manifest = "{}"
    detail = json.loads(
        snapshot_authority_detail(
            snapshot_id="snapshot-1",
            manifest_json=manifest,
            audit_ids={},
        )
    )
    detail[field] = value
    with pytest.raises(RosterSyncError, match=message):
        validate_snapshot_authority_detail(
            json.dumps(detail, sort_keys=True, separators=(",", ":")),
            snapshot_id="snapshot-1",
            manifest_json=manifest,
            candidate_ids=[],
        )


def test_candidate_authority_rejects_backdated_late_approval_row() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_candidate_status_events ("
        "id TEXT, candidate_id TEXT, event_type TEXT, from_status TEXT, to_status TEXT, "
        "reason TEXT, audit_id TEXT, created_at TEXT)"
    )
    audit_id = "audit-" + ("a" * 64)
    rows = [
        (
            "event-activated",
            "candidate-1",
            "activated",
            "approved",
            "activated",
            "snapshot_id=snapshot-1",
            audit_id,
            "2026-01-02T00:00:00+00:00",
        ),
        (
            "event-approved",
            "candidate-1",
            "approved",
            "pending",
            "approved",
            "snapshot_id=snapshot-1",
            audit_id,
            "2026-01-01T00:00:00+00:00",
        ),
    ]
    conn.executemany(
        "INSERT INTO agent_candidate_status_events "
        "(id, candidate_id, event_type, from_status, to_status, reason, audit_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    try:
        with pytest.raises(ValueError, match="transitions are invalid"):
            roster_authority_subject._authority_events(
                conn,
                candidate_id="candidate-1",
            )
    finally:
        conn.close()


def test_snapshot_authority_rejects_backdated_late_approval_row() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_import_events ("
        "id TEXT, event_sequence INTEGER, event_type TEXT, agent_slug TEXT, detail TEXT, "
        "created_at TEXT)"
    )
    audit_id = "audit-" + ("a" * 64)
    manifest = '{"approved":true,"candidates":[]}'
    detail = snapshot_authority_detail(
        snapshot_id="snapshot-1",
        manifest_json=manifest,
        audit_ids={"candidate-1": audit_id},
    )
    conn.executemany(
        "INSERT INTO agent_import_events "
        "(id, event_sequence, event_type, agent_slug, detail, created_at) "
        "VALUES (?, ?, ?, '', ?, ?)",
        [
            (
                "event-activated",
                1,
                "snapshot_activated",
                detail,
                "2026-01-02T00:00:00+00:00",
            ),
            (
                "event-approved",
                2,
                "snapshot_approved",
                detail,
                "2026-01-01T00:00:00+00:00",
            ),
        ],
    )
    try:
        with pytest.raises(ValueError, match="authority is invalid"):
            roster_authority_subject._snapshot_events(
                conn,
                snapshot_id="snapshot-1",
                manifest_json=manifest,
                candidate_ids=["candidate-1"],
                candidate_id="candidate-1",
                approved_audit_id=audit_id,
                activated_audit_id=audit_id,
            )
    finally:
        conn.close()


def test_snapshot_authority_rejects_oversized_duplicate_before_json1() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_import_events ("
        "event_sequence INTEGER, event_type TEXT, agent_slug TEXT, detail TEXT, "
        "created_at TEXT)"
    )
    audit_id = "audit-" + ("a" * 64)
    manifest = '{"approved":true,"candidates":[]}'
    detail = snapshot_authority_detail(
        snapshot_id="snapshot-1",
        manifest_json=manifest,
        audit_ids={"candidate-1": audit_id},
    )
    conn.executemany(
        "INSERT INTO agent_import_events "
        "(event_sequence, event_type, agent_slug, detail, created_at) "
        "VALUES (?, ?, '', ?, ?)",
        [
            (1, "snapshot_approved", detail, "2026-01-01T00:00:00+00:00"),
            (2, "snapshot_activated", detail, "2026-01-02T00:00:00+00:00"),
            (
                3,
                "snapshot_approved",
                "x" * (snapshot_authority_subject.MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES + 1),
                "2026-01-03T00:00:00+00:00",
            ),
        ],
    )
    try:
        with pytest.raises(ValueError, match="unsafe event detail"):
            roster_authority_subject._snapshot_events(
                conn,
                snapshot_id="snapshot-1",
                manifest_json=manifest,
                candidate_ids=["candidate-1"],
                candidate_id="candidate-1",
                approved_audit_id=audit_id,
                activated_audit_id=audit_id,
            )
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("unsafe_detail", "message"),
    [
        ("{", "invalid event detail"),
        (sqlite3.Binary(b"{}"), "unsafe event detail"),
    ],
)
def test_snapshot_authority_rejects_invalid_or_nontext_detail_before_json1(
    unsafe_detail: object,
    message: str,
) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_import_events ("
        "event_sequence INTEGER, event_type TEXT, agent_slug TEXT, detail, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO agent_import_events "
        "(event_sequence, event_type, agent_slug, detail, created_at) "
        "VALUES (1, 'snapshot_approved', '', ?, '2026-01-01T00:00:00+00:00')",
        (unsafe_detail,),
    )
    try:
        with pytest.raises(ValueError, match=message):
            roster_authority_subject._snapshot_events(
                conn,
                snapshot_id="snapshot-1",
                manifest_json="{}",
                candidate_ids=[],
                candidate_id="candidate-1",
                approved_audit_id="audit-" + ("a" * 64),
                activated_audit_id="audit-" + ("a" * 64),
            )
    finally:
        conn.close()


def test_bound_audit_helper_validates_immutable_identity_without_rebasing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "bound-audit.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate_id = quarantine_candidate(
        _governed_candidate("bound-audit-reviewer", "Review one bounded audit."),
        source_id,
        store,
    )
    conn = store._connect()
    try:
        audit_id, version, candidate_hash = _audit_binding(conn, candidate_id)
        audit, policy_current = assert_bound_candidate_audit_from_connection(
            conn,
            audit_id=audit_id,
            candidate_id=candidate_id,
            candidate_version=version,
            candidate_hash=candidate_hash,
            require_current_policy=False,
        )
        assert audit["id"] == audit_id
        assert policy_current is True

        monkeypatch.setattr(review_subject, "AUDIT_POLICY_HASH", "b" * 64)
        historical, historical_policy_current = assert_bound_candidate_audit_from_connection(
            conn,
            audit_id=audit_id,
            candidate_id=candidate_id,
            candidate_version=version,
            candidate_hash=candidate_hash,
            require_current_policy=False,
        )
        assert historical["id"] == audit_id
        assert historical_policy_current is False
        with pytest.raises(RosterSyncError, match="bound passing audit"):
            assert_bound_candidate_audit_from_connection(
                conn,
                audit_id=audit_id,
                candidate_id=candidate_id,
                candidate_version=version,
                candidate_hash=candidate_hash,
                require_current_policy=True,
            )
    finally:
        conn.close()


def test_bound_audit_helper_rejects_oversized_inference_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "oversized-audit-evidence.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate_id = quarantine_candidate(
        _governed_candidate("oversized-audit-reviewer", "Review bounded evidence."),
        source_id,
        store,
    )
    conn = store._connect()
    try:
        audit_id, version, candidate_hash = _audit_binding(conn, candidate_id)
        oversized = json.dumps({"blob": "x" * MAX_INFERENCE_EVIDENCE_BYTES})
        conn.execute(
            "UPDATE agent_candidate_audits SET inference_evidence = ? WHERE id = ?",
            (oversized, audit_id),
        )
        with pytest.raises(RosterSyncError, match="inference audit evidence is invalid"):
            assert_bound_candidate_audit_from_connection(
                conn,
                audit_id=audit_id,
                candidate_id=candidate_id,
                candidate_version=version,
                candidate_hash=candidate_hash,
                require_current_policy=False,
            )
    finally:
        conn.close()


def test_bound_audit_helper_rejects_nontext_or_structurally_unbounded_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "structured-audit-evidence.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate_id = quarantine_candidate(
        _governed_candidate("structured-audit-reviewer", "Review structured evidence."),
        source_id,
        store,
    )
    conn = store._connect()
    try:
        audit_id, version, candidate_hash = _audit_binding(conn, candidate_id)
        payloads: list[object] = [
            sqlite3.Binary(b"{}"),
            ('{"nested":' * 7) + "null" + ("}" * 7),
            json.dumps({"nodes": list(range(129))}),
        ]
        for payload in payloads:
            conn.execute(
                "UPDATE agent_candidate_audits SET inference_evidence = ? WHERE id = ?",
                (payload, audit_id),
            )
            with pytest.raises(RosterSyncError, match="inference audit evidence"):
                assert_bound_candidate_audit_from_connection(
                    conn,
                    audit_id=audit_id,
                    candidate_id=candidate_id,
                    candidate_version=version,
                    candidate_hash=candidate_hash,
                    require_current_policy=False,
                )
    finally:
        conn.close()


def test_bound_audit_helper_rejects_unbounded_findings(tmp_path: Path) -> None:
    store = Store(tmp_path / "unbounded-audit-findings.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate_id = quarantine_candidate(
        _governed_candidate("unbounded-audit-reviewer", "Review bounded findings."),
        source_id,
        store,
    )
    conn = store._connect()
    try:
        audit_id, version, candidate_hash = _audit_binding(conn, candidate_id)
        audit = conn.execute(
            "SELECT created_at FROM agent_candidate_audits WHERE id = ?",
            (audit_id,),
        ).fetchone()
        assert audit is not None
        conn.execute(
            "DELETE FROM agent_candidate_audit_findings WHERE audit_id = ?",
            (audit_id,),
        )
        conn.executemany(
            "INSERT INTO agent_candidate_audit_findings "
            "(id, audit_id, source, severity, code, message, evidence_hash, created_at) "
            "VALUES (?, ?, 'deterministic', 'info', ?, 'finding', ?, ?)",
            [
                (
                    f"overflow-{index}",
                    audit_id,
                    f"overflow_{index}",
                    f"{index:064x}",
                    audit["created_at"],
                )
                for index in range(MAX_AUDIT_FINDINGS + 1)
            ],
        )
        with pytest.raises(RosterSyncError, match="findings exceed the limit"):
            assert_bound_candidate_audit_from_connection(
                conn,
                audit_id=audit_id,
                candidate_id=candidate_id,
                candidate_version=version,
                candidate_hash=candidate_hash,
                require_current_policy=False,
            )
    finally:
        conn.close()


@pytest.mark.parametrize("operation", ["activate", "if_missing", "bulk", "upsert"])
def test_public_activation_rejects_unknown_before_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    store = Store(tmp_path / f"{operation}.db")
    unknown = _private_agent("unknown-specialist", version="1.0.0", prompt="Unknown.")

    def unexpected_connect() -> Any:
        raise AssertionError("invalid public activation opened the store")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    with pytest.raises(ValueError, match="exact approved bundled"):
        if operation == "activate":
            store.activate_agent(unknown)
        elif operation == "if_missing":
            store.activate_agent_if_missing(unknown)
        elif operation == "bulk":
            store.activate_agents_if_missing([unknown])
        else:
            store.upsert_roster_entry(unknown)


def test_public_mixed_batch_is_prevalidated_and_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def unexpected_connect() -> Any:
        raise AssertionError("invalid public batch opened the store")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    with pytest.raises(ValueError, match="exact approved bundled"):
        store.activate_agents_if_missing(
            [
                _canonical(),
                _private_agent("unknown-specialist", version="1.0.0", prompt="Unknown."),
            ]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slug", "code_reviewer"),
        ("description", "Unaudited replacement description."),
        ("prompt_body", "Unaudited replacement prompt."),
        ("ignored_authority_override", "approve"),
    ],
)
def test_public_activation_rejects_changed_bundled_contract_before_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    store = Store(tmp_path / f"{field}.db")
    changed = {**_canonical(), field: value}

    def unexpected_connect() -> Any:
        raise AssertionError("changed bundled contract opened the store")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    with pytest.raises(ValueError, match=r"bundled roster contract|exact approved bundled"):
        store.activate_agent(changed)


def test_exact_bundle_public_activation_is_idempotent_and_non_replacing(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = _canonical()
    store.activate_agent(canonical)
    initial = store.get_roster_entry(canonical["slug"])
    generation = _generation(store)

    store.activate_agent(dict(canonical))
    store.upsert_roster_entry(dict(canonical))
    assert store.activate_agent_if_missing(dict(canonical)) is False
    assert store.activate_agents_if_missing([dict(canonical)]) == 0

    assert store.get_roster_entry(canonical["slug"]) == initial
    assert _generation(store) == generation


def test_exact_bundle_seed_preserves_approved_candidate_active_revision(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate, _snapshot_id, _candidate_id = _activate_candidate(
        store,
        source_id,
        slug="code-reviewer",
        prompt="Approved operator revision.",
    )
    canonical = _canonical()

    store.activate_agent(canonical)
    store.upsert_roster_entry(canonical)
    assert store.activate_agent_if_missing(canonical) is False
    assert store.activate_agents_if_missing([canonical]) == 0

    assert store.get_roster_entry("code-reviewer") == candidate


def test_private_prevalidated_boundary_requires_explicit_safe_content_before_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def unexpected_connect() -> Any:
        raise AssertionError("invalid private activation opened the store")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    with pytest.raises(ValueError, match="behavior content"):
        store._activate_prevalidated_agent({"slug": "missing-content", "name": "Missing"})

    canonical = _canonical()
    aliased = {**canonical, "slug": "code_reviewer"}
    with pytest.raises(ValueError, match="bundled roster contract"):
        store._activate_prevalidated_agent(aliased)


def test_candidate_revision_rollback_requires_and_accepts_complete_authority(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    first, _first_snapshot, _first_candidate = _activate_candidate(
        store,
        source_id,
        slug="rollback-reviewer",
        prompt="First approved prompt.",
    )
    second, _second_snapshot, _second_candidate = _activate_candidate(
        store,
        source_id,
        slug="rollback-reviewer",
        prompt="Second approved prompt.",
    )

    restored = store.rollback_agent_revision(
        "rollback-reviewer",
        first["version"],
        expected_current_version=second["version"],
        expected_current_hash=second["hash"],
    )

    assert restored["version"] == first["version"]
    assert restored["hash"] == first["hash"]


def test_current_bundle_revision_is_a_valid_rollback_target(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = _canonical()
    store.activate_agent(canonical)
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    candidate, _snapshot_id, _candidate_id = _activate_candidate(
        store,
        source_id,
        slug=canonical["slug"],
        prompt="Approved replacement prompt.",
    )

    restored = store.rollback_agent_revision(
        canonical["slug"],
        canonical["version"],
        expected_current_version=candidate["version"],
        expected_current_hash=candidate["hash"],
    )

    assert restored["version"] == canonical["version"]
    assert restored["hash"] == canonical["hash"]
    assert store.get_specialist_prompt(canonical["slug"])["prompt_body"] == canonical["prompt_body"]


def test_unproven_revision_cannot_authorize_change_or_noop(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        _private_agent("private-reviewer", version="1.0.0", prompt="First private prompt.")
    )
    first = store.get_roster_entry("private-reviewer")
    store._activate_prevalidated_agent(
        _private_agent("private-reviewer", version="2.0.0", prompt="Second private prompt.")
    )
    second = store.get_roster_entry("private-reviewer")
    generation = _generation(store)

    with pytest.raises(ValueError, match="activation authority"):
        store.rollback_agent_revision(
            "private-reviewer",
            first["version"],
            expected_current_version=second["version"],
            expected_current_hash=second["hash"],
        )
    with pytest.raises(ValueError, match="activation authority"):
        store.rollback_agent_revision(
            "private-reviewer",
            second["version"],
            expected_current_version=second["version"],
            expected_current_hash=second["hash"],
        )

    assert store.get_roster_entry("private-reviewer") == second
    assert _generation(store) == generation


def test_noop_rollback_rejects_tampered_active_projection(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    active, _snapshot_id, _candidate_id = _activate_candidate(
        store,
        source_id,
        slug="projection-reviewer",
        prompt="Approved prompt.",
    )
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_active SET description = 'tampered' WHERE agent_slug = ?",
            ("projection-reviewer",),
        )
        conn.commit()
    finally:
        conn.close()
    generation = _generation(store)

    with pytest.raises(ValueError, match="active revision projection"):
        store.rollback_agent_revision(
            "projection-reviewer",
            active["version"],
            expected_current_version=active["version"],
            expected_current_hash=active["hash"],
        )

    assert _generation(store) == generation
    assert store.get_roster_entry("projection-reviewer")["description"] == "tampered"


def _delete_approved_status(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "DELETE FROM agent_candidate_status_events WHERE event_type = 'approved' AND reason = ?",
        (f"snapshot_id={snapshot_id}",),
    )


def _unbind_approved_audit(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "UPDATE agent_candidate_status_events SET audit_id = '' "
        "WHERE event_type = 'approved' AND reason = ?",
        (f"snapshot_id={snapshot_id}",),
    )


def _delete_snapshot_approved(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "DELETE FROM agent_import_events WHERE event_type = 'snapshot_approved' "
        "AND json_valid(detail) AND json_extract(detail, '$.snapshot_id') = ?",
        (snapshot_id,),
    )


def _disagree_snapshot_approval(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "UPDATE agent_snapshots SET approved = 0 WHERE snapshot_id = ?",
        (snapshot_id,),
    )


def _malform_snapshot_manifest(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "UPDATE agent_snapshots SET manifest = '{}' WHERE snapshot_id = ?",
        (snapshot_id,),
    )


def _invalidate_bound_audit_policy(conn: Any, snapshot_id: str) -> None:
    row = conn.execute(
        "SELECT audit_id FROM agent_candidate_status_events "
        "WHERE event_type = 'approved' AND reason = ?",
        (f"snapshot_id={snapshot_id}",),
    ).fetchone()
    assert row is not None
    conn.execute(
        "UPDATE agent_candidate_audits SET policy_hash = 'stale-policy' WHERE id = ?",
        (row["audit_id"],),
    )


def _reverse_cross_event_order(conn: Any, snapshot_id: str) -> None:
    conn.execute(
        "UPDATE agent_import_events SET created_at = '9999-12-31T23:59:59+00:00' "
        "WHERE event_type = 'snapshot_approved' AND json_valid(detail) "
        "AND json_extract(detail, '$.snapshot_id') = ?",
        (snapshot_id,),
    )


def _duplicate_activation_status(conn: Any, snapshot_id: str) -> None:
    row = conn.execute(
        "SELECT candidate_id, event_type, from_status, to_status, reason, audit_id, created_at "
        "FROM agent_candidate_status_events "
        "WHERE event_type = 'activated' AND reason = ?",
        (f"snapshot_id={snapshot_id}",),
    ).fetchone()
    assert row is not None
    conn.execute(
        "INSERT INTO agent_candidate_status_events "
        "(id, candidate_id, event_type, from_status, to_status, reason, audit_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "duplicate-activation-event",
            row["candidate_id"],
            row["event_type"],
            row["from_status"],
            row["to_status"],
            row["reason"],
            row["audit_id"],
            row["created_at"],
        ),
    )


@pytest.mark.parametrize(
    "tamper",
    [
        _delete_approved_status,
        _unbind_approved_audit,
        _delete_snapshot_approved,
        _disagree_snapshot_approval,
        _malform_snapshot_manifest,
        _invalidate_bound_audit_policy,
        _reverse_cross_event_order,
        _duplicate_activation_status,
    ],
)
def test_forged_or_malformed_authority_cannot_enable_rollback(
    tmp_path: Path,
    tamper: Callable[[Any, str], None],
) -> None:
    store = Store(tmp_path / f"{tamper.__name__}.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    first, first_snapshot, _first_candidate = _activate_candidate(
        store,
        source_id,
        slug="authority-reviewer",
        prompt="First approved prompt.",
    )
    second, _second_snapshot, _second_candidate = _activate_candidate(
        store,
        source_id,
        slug="authority-reviewer",
        prompt="Second approved prompt.",
    )
    conn = store._connect()
    try:
        tamper(conn, first_snapshot)
        conn.commit()
    finally:
        conn.close()
    generation = _generation(store)

    with pytest.raises((ValueError, RosterSyncError)):
        store.rollback_agent_revision(
            "authority-reviewer",
            first["version"],
            expected_current_version=second["version"],
            expected_current_hash=second["hash"],
        )

    assert store.get_roster_entry("authority-reviewer") == second
    assert _generation(store) == generation


def test_identical_cross_table_timestamps_preserve_valid_authority(tmp_path: Path) -> None:
    store = Store(tmp_path / "identical-timestamps.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    first, first_snapshot, _first_candidate = _activate_candidate(
        store,
        source_id,
        slug="timestamp-reviewer",
        prompt="First approved prompt.",
    )
    second, _second_snapshot, _second_candidate = _activate_candidate(
        store,
        source_id,
        slug="timestamp-reviewer",
        prompt="Second approved prompt.",
    )
    frozen = "9999-12-31T23:59:59+00:00"
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_candidate_status_events SET created_at = ? "
            "WHERE event_type IN ('approved', 'activated') AND reason = ?",
            (frozen, f"snapshot_id={first_snapshot}"),
        )
        conn.execute(
            "UPDATE agent_import_events SET created_at = ? "
            "WHERE event_type IN ('snapshot_approved', 'snapshot_activated') "
            "AND json_valid(detail) AND json_extract(detail, '$.snapshot_id') = ?",
            (frozen, first_snapshot),
        )
        conn.commit()
    finally:
        conn.close()

    restored = store.rollback_agent_revision(
        "timestamp-reviewer",
        first["version"],
        expected_current_version=second["version"],
        expected_current_hash=second["hash"],
    )
    assert restored["version"] == first["version"]
