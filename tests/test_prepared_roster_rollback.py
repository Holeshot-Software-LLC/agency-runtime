"""TOCTOU and exact-effect tests for owner-requested roster rollback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config_binding import StoreConfigBindingError
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.revisions import content_digest, serialized_revision_metadata
from agency_runtime.core.roster.sync import (
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    quarantine_candidate,
)
from agency_runtime.core.store import roster as roster_subject
from agency_runtime.core.store.roster import _RosterRollbackBinding
from agency_runtime.core.store.roster_authority import RevisionActivationAuthority
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.identity import stable_worker_id


class _EqualityText(str):
    def __eq__(self, _other: object) -> bool:
        return True


class _EqualityInt(int):
    def __eq__(self, _other: object) -> bool:
        return True


def _synthetic_binding() -> _RosterRollbackBinding:
    return _RosterRollbackBinding(
        config_path=r"C:\Users\owner\.agency-runtime\config.yaml",
        database_path=r"C:\Users\owner\.agency-runtime\agency.db",
        database_device=7,
        database_inode=11,
        roster_generation=5,
        slug="security-reviewer",
        current_version="sha256:" + "1" * 64,
        current_hash="2" * 64,
        current_projection_digest="3" * 64,
        target_revision_id="revision-1",
        target_version="sha256:" + "4" * 64,
        target_hash="5" * 64,
        target_content_metadata_digest="6" * 64,
        activation_authority_kind="bundled",
        activation_authority_digest="7" * 64,
        workforce_identity_digest="8" * 64,
    )


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


def _prepared_bundle_target(
    tmp_path: Path,
) -> tuple[Store, dict[str, Any], dict[str, Any], _RosterRollbackBinding]:
    store = Store(tmp_path / "agency.db")
    canonical = _canonical()
    store.activate_agent(canonical)
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    current, _snapshot_id, _candidate_id = _activate_candidate(
        store,
        source_id,
        slug=canonical["slug"],
        prompt="Approved replacement prompt.",
    )
    prepared = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )
    return store, canonical, current, prepared


def _prepared_candidate_target(
    tmp_path: Path,
) -> tuple[Store, dict[str, Any], dict[str, Any], str, _RosterRollbackBinding]:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "source"), "source")
    first, _first_snapshot, first_candidate_id = _activate_candidate(
        store,
        source_id,
        slug="rollback-reviewer",
        prompt="First approved prompt.",
    )
    second, _second_snapshot, _second_candidate_id = _activate_candidate(
        store,
        source_id,
        slug="rollback-reviewer",
        prompt="Second approved prompt.",
    )
    prepared = store._prepare_agent_revision_rollback(
        "rollback-reviewer",
        first["version"],
        expected_current_version=second["version"],
        expected_current_hash=second["hash"],
    )
    return store, first, second, first_candidate_id, prepared


def _one(conn: Any, statement: str, values: tuple[object, ...] = ()) -> dict[str, Any]:
    row = conn.execute(statement, values).fetchone()
    assert row is not None
    return dict(row)


def _commit(store: Store, prepared: _RosterRollbackBinding) -> dict[str, Any]:
    """Exercise the private commit primitive with its exact coordinator binding."""

    return store._commit_prepared_agent_revision_rollback(
        prepared,
        prepared_primitives=tuple(prepared),
    )


def _append_target_projection(
    store: Store,
    prepared: _RosterRollbackBinding,
    *,
    valid_hash: bool = True,
    authority: str = "agency-runtime-package",
    parent_hash: str | None = None,
) -> None:
    conn = store._connect()
    try:
        lineage = _one(
            conn,
            "SELECT recruitment_contract, recruitment_contract_hash "
            "FROM agent_version_lineage WHERE agent_version_id = ?",
            (prepared.target_revision_id,),
        )
        worker = _one(
            conn,
            "SELECT worker_id FROM agent_workers WHERE agent_slug = ?",
            (prepared.slug,),
        )
        sequence = int(
            _one(
                conn,
                "SELECT COALESCE(MAX(projection_sequence), 0) + 1 AS value "
                "FROM agent_recruitment_contract_projections",
            )["value"]
        )
        document = str(lineage["recruitment_contract"])
        digest = str(lineage["recruitment_contract_hash"]) if valid_hash else "0" * 64
        latest = conn.execute(
            "SELECT recruitment_contract_hash "
            "FROM agent_recruitment_contract_projections "
            "WHERE worker_id = ? AND agent_version_id = ? "
            "ORDER BY projection_sequence DESC LIMIT 1",
            (worker["worker_id"], prepared.target_revision_id),
        ).fetchone()
        expected_parent = (
            str(lineage["recruitment_contract_hash"])
            if latest is None
            else str(latest["recruitment_contract_hash"])
        )
        conn.execute(
            "INSERT INTO agent_recruitment_contract_projections "
            "(id, projection_sequence, worker_id, agent_version_id, "
            "parent_contract_hash, recruitment_contract, recruitment_contract_hash, "
            "projection_authority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"projection-{sequence}",
                sequence,
                worker["worker_id"],
                prepared.target_revision_id,
                expected_parent if parent_hash is None else parent_hash,
                document,
                digest,
                authority,
                f"2026-07-27T00:00:{sequence:02d}+00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _effect_snapshot(store: Store, slug: str) -> dict[str, Any]:
    conn = store._connect()
    try:
        worker = _one(
            conn,
            "SELECT * FROM agent_workers WHERE agent_slug = ?",
            (slug,),
        )
        return {
            "active": _one(
                conn,
                "SELECT * FROM agent_active WHERE agent_slug = ?",
                (slug,),
            ),
            "categories": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM agent_categories WHERE agent_slug = ? ORDER BY category",
                    (slug,),
                ).fetchall()
            ],
            "worker": worker,
            "rollback_events": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM agent_import_events "
                    "WHERE event_type = 'agent_revision_rolled_back' AND agent_slug = ? "
                    "ORDER BY event_sequence",
                    (slug,),
                ).fetchall()
            ],
            "worker_events": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM agent_worker_events WHERE worker_id = ? ORDER BY event_sequence",
                    (worker["worker_id"],),
                ).fetchall()
            ],
            "generation": _one(
                conn,
                "SELECT value FROM store_counters WHERE name = 'roster-generation'",
            )["value"],
        }
    finally:
        conn.close()


def test_prepare_freezes_json_free_store_roster_and_authority_identities(tmp_path: Path) -> None:
    _store, canonical, current, prepared = _prepared_bundle_target(tmp_path)

    assert prepared.slug == canonical["slug"]
    assert prepared.current_version == current["version"]
    assert prepared.target_version == canonical["version"]
    assert prepared.target_hash == canonical["hash"]
    assert prepared.activation_authority_kind == "bundled"
    assert prepared.database_inode > 0
    assert all(
        type(getattr(prepared, field)) in {str, int} for field in _RosterRollbackBinding._fields
    )


def test_unverified_positive_store_apis_are_not_public() -> None:
    assert not hasattr(Store, "prepare_agent_revision_rollback")
    assert not hasattr(Store, "commit_prepared_agent_revision_rollback")
    assert callable(Store.rollback_agent_revision)


@pytest.mark.parametrize("field", _RosterRollbackBinding._fields)
def test_coordinator_rejects_non_builtin_primitive_in_every_binding_field(
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = roster_subject.RosterStoreMixin()
    binding = _synthetic_binding()
    original = getattr(binding, field)
    injected: object
    if type(original) is int:
        injected = True if field == "database_device" else _EqualityInt(original)
    else:
        injected = _EqualityText(original)
    forged = binding._replace(**{field: injected})
    monkeypatch.setattr(
        roster_subject.RosterStoreMixin,
        "_prepare_agent_revision_rollback",
        lambda *_args, **_kwargs: forged,
    )
    with pytest.raises(ValueError, match="binding is invalid"):
        owner.rollback_agent_revision(
            "security-reviewer",
            "sha256:" + "4" * 64,
            expected_current_version="sha256:" + "1" * 64,
            expected_current_hash="2" * 64,
        )


def test_public_coordinator_owns_prepare_and_same_store_commit_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, canonical, current, _prepared = _prepared_bundle_target(tmp_path)
    calls: list[tuple[str, int, tuple[str | int, ...]]] = []
    original_prepare = roster_subject.RosterStoreMixin._prepare_agent_revision_rollback
    original_commit = roster_subject.RosterStoreMixin._commit_prepared_agent_revision_rollback

    def prepare(owner: object, *args: object, **kwargs: object) -> _RosterRollbackBinding:
        binding = original_prepare(owner, *args, **kwargs)
        calls.append(("prepare", id(owner), tuple(binding)))
        return binding

    def commit(
        owner: object,
        binding: _RosterRollbackBinding,
        *,
        prepared_primitives: tuple[str | int, ...],
    ) -> dict[str, Any]:
        assert prepared_primitives == tuple(binding)
        calls.append(("commit", id(owner), prepared_primitives))
        return original_commit(
            owner,
            binding,
            prepared_primitives=prepared_primitives,
        )

    monkeypatch.setattr(
        roster_subject.RosterStoreMixin,
        "_prepare_agent_revision_rollback",
        prepare,
    )
    monkeypatch.setattr(
        roster_subject.RosterStoreMixin,
        "_commit_prepared_agent_revision_rollback",
        commit,
    )

    restored = store.rollback_agent_revision(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )

    assert restored["version"] == canonical["version"]
    assert [stage for stage, _store_id, _binding in calls] == ["prepare", "commit"]
    assert {store_id for _stage, store_id, _binding in calls} == {id(store)}
    assert calls[0][2] == calls[1][2]


def test_prepared_rollback_rejects_noop_before_commit(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = _canonical()
    store.activate_agent(canonical)
    generation = store.get_roster_generation()

    with pytest.raises(ValueError, match="already active"):
        store._prepare_agent_revision_rollback(
            canonical["slug"],
            canonical["version"],
            expected_current_version=canonical["version"],
            expected_current_hash=canonical["hash"],
        )

    assert store.get_roster_generation() == generation


def test_commit_rejects_config_lexical_identity_drift(tmp_path: Path) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    store.config_path = tmp_path / "retargeted-config.yaml"

    with pytest.raises(StoreConfigBindingError, match="configuration identity changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_rejects_database_inode_drift_through_trusted_identity_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    monkeypatch.setattr(
        roster_subject,
        "_database_identity_for_prepared_rollback",
        lambda _store: (prepared.database_device, prepared.database_inode + 1),
    )

    with pytest.raises(PermissionError, match="database identity changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_rejects_global_generation_drift(tmp_path: Path) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute("UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_rejects_exact_current_revision_projection_drift(tmp_path: Path) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET created_at = created_at || '-drift' "
            "WHERE agent_slug = ? AND version = ?",
            (prepared.slug, prepared.current_version),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_rejects_current_active_projection_drift(tmp_path: Path) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_active SET description = description || ' drift' WHERE agent_slug = ?",
            (prepared.slug,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="active revision projection failed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


@pytest.mark.parametrize("field", ["source_id", "source_version"])
def test_commit_full_target_digest_rejects_source_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    frozen_authority = RevisionActivationAuthority(
        kind=prepared.activation_authority_kind,
        projection=(),
        digest=prepared.activation_authority_digest,
    )
    monkeypatch.setattr(
        roster_subject,
        "assert_revision_activation_authority",
        lambda *_args, **_kwargs: frozen_authority,
    )
    conn = store._connect()
    try:
        conn.execute(
            f"UPDATE agent_versions SET {field} = ? WHERE id = ?",  # nosec B608
            (f"drifted-{field}", prepared.target_revision_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def _freeze_authority(prepared: _RosterRollbackBinding) -> RevisionActivationAuthority:
    return RevisionActivationAuthority(
        kind=prepared.activation_authority_kind,
        projection=(),
        digest=prepared.activation_authority_digest,
    )


def test_commit_full_target_digest_rejects_content_drift_with_stable_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    monkeypatch.setattr(
        roster_subject,
        "assert_revision_activation_authority",
        lambda *_args, **_kwargs: _freeze_authority(prepared),
    )
    conn = store._connect()
    try:
        target = _one(
            conn,
            "SELECT content FROM agent_versions WHERE id = ?",
            (prepared.target_revision_id,),
        )
        changed = str(target["content"]) + "\nDrifted after operator preparation."
        conn.execute(
            "UPDATE agent_versions SET content = ?, hash = ? WHERE id = ?",
            (changed, content_digest(changed), prepared.target_revision_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(
        ValueError,
        match=r"prepared rollback state changed|lineage contract identity is invalid",
    ):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_full_target_digest_rejects_metadata_drift_with_stable_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    monkeypatch.setattr(
        roster_subject,
        "assert_revision_activation_authority",
        lambda *_args, **_kwargs: _freeze_authority(prepared),
    )
    conn = store._connect()
    try:
        target = _one(
            conn,
            "SELECT metadata FROM agent_versions WHERE id = ?",
            (prepared.target_revision_id,),
        )
        metadata = json.loads(str(target["metadata"]))
        metadata["description"] = str(metadata["description"]) + " drift"
        conn.execute(
            "UPDATE agent_versions SET metadata = ? WHERE id = ?",
            (serialized_revision_metadata(metadata), prepared.target_revision_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


@pytest.mark.parametrize("identity", ["worker", "current_lineage", "target_lineage"])
def test_commit_rejects_worker_and_lineage_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: str,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        if identity == "worker":
            conn.execute(
                "UPDATE agent_workers SET current_hash = ? WHERE agent_slug = ?",
                ("0" * 64, prepared.slug),
            )
        else:
            identity_reader = roster_subject._workforce_rollback_identity

            def drifted_lineage_identity(*args: object, **kwargs: object) -> tuple[dict, str]:
                worker, _digest = identity_reader(*args, **kwargs)
                return worker, ("1" if identity == "current_lineage" else "2") * 64

            monkeypatch.setattr(
                roster_subject,
                "_workforce_rollback_identity",
                drifted_lineage_identity,
            )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(
        ValueError,
        match=r"workforce identity|prepared rollback state changed",
    ):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_binds_explicit_absence_of_target_contract_projection(
    tmp_path: Path,
) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared)

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_commit_rejects_latest_target_contract_projection_drift(tmp_path: Path) -> None:
    store, canonical, current, initial = _prepared_bundle_target(tmp_path)
    _append_target_projection(store, initial)
    prepared = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared)

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


@pytest.mark.parametrize("projection_count", [1, 2])
def test_valid_target_contract_projection_chain_can_be_committed(
    tmp_path: Path,
    projection_count: int,
) -> None:
    store, canonical, current, initial = _prepared_bundle_target(tmp_path)
    for _index in range(projection_count):
        _append_target_projection(store, initial)
    prepared = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )

    restored = _commit(store, prepared)

    assert restored["version"] == canonical["version"]


def test_commit_rejects_arbitrary_target_projection_authority(tmp_path: Path) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared, authority="test-fixture")

    with pytest.raises(ValueError, match="projection chain is invalid"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_commit_rejects_broken_first_target_projection_parent(tmp_path: Path) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared, parent_hash="f" * 64)

    with pytest.raises(ValueError, match="projection chain is invalid"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_commit_rejects_broken_later_target_projection_parent(tmp_path: Path) -> None:
    store, canonical, current, initial = _prepared_bundle_target(tmp_path)
    _append_target_projection(store, initial)
    prepared = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared, parent_hash="e" * 64)

    with pytest.raises(ValueError, match="projection chain is invalid"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_commit_rejects_invalid_latest_target_contract_projection(tmp_path: Path) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    _append_target_projection(store, prepared, valid_hash=False)

    with pytest.raises(ValueError, match="projection contract is invalid"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_commit_rejects_invalid_target_lineage_contract(tmp_path: Path) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    conn = store._connect()
    try:
        conn.execute("DROP TRIGGER agency_version_lineage_immutable_update")
        conn.execute(
            "UPDATE agent_version_lineage SET recruitment_contract_hash = ? "
            "WHERE agent_version_id = ?",
            ("0" * 64, prepared.target_revision_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="lineage contract is invalid"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_absent_upstream_target_lineage_binds_deterministic_generated_contract(
    tmp_path: Path,
) -> None:
    store, canonical, current, initial = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute("DROP TRIGGER agency_version_lineage_immutable_delete")
        conn.execute(
            "DELETE FROM agent_version_lineage WHERE agent_version_id = ?",
            (initial.target_revision_id,),
        )
        conn.commit()
    finally:
        conn.close()
    first = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )
    second = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )
    assert first.workforce_identity_digest == second.workforce_identity_digest

    _commit(store, first)

    conn = store._connect()
    try:
        lineage = _one(
            conn,
            "SELECT recruitment_contract, recruitment_contract_hash "
            "FROM agent_version_lineage WHERE agent_version_id = ?",
            (first.target_revision_id,),
        )
    finally:
        conn.close()
    document = str(lineage["recruitment_contract"])
    contract = json.loads(document)
    assert content_digest(document) == lineage["recruitment_contract_hash"]
    assert contract["worker_id"] == stable_worker_id(canonical["slug"])
    assert contract["agent_id"] == canonical["slug"]
    assert contract["version"] == canonical["version"]
    assert contract["version_hash"].removeprefix("sha256:") == canonical["hash"]


@pytest.mark.parametrize(
    ("historical_employment", "historical_enabled"),
    [("contractor", True), ("disabled", False)],
)
def test_rollback_preserves_current_lifecycle_over_historical_contract_values(
    tmp_path: Path,
    historical_employment: str,
    historical_enabled: bool,
) -> None:
    store, canonical, current, initial = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        lineage = _one(
            conn,
            "SELECT recruitment_contract FROM agent_version_lineage WHERE agent_version_id = ?",
            (initial.target_revision_id,),
        )
        historical = json.loads(str(lineage["recruitment_contract"]))
        historical["employment"] = historical_employment
        historical["enabled"] = historical_enabled
        document = json.dumps(historical, sort_keys=True, separators=(",", ":"))
        conn.execute("DROP TRIGGER agency_version_lineage_immutable_update")
        conn.execute(
            "UPDATE agent_version_lineage SET recruitment_contract = ?, "
            "recruitment_contract_hash = ? WHERE agent_version_id = ?",
            (document, content_digest(document), initial.target_revision_id),
        )
        conn.commit()
    finally:
        conn.close()
    prepared = store._prepare_agent_revision_rollback(
        canonical["slug"],
        canonical["version"],
        expected_current_version=current["version"],
        expected_current_hash=current["hash"],
    )

    _commit(store, prepared)

    conn = store._connect()
    try:
        worker = _one(
            conn,
            "SELECT employment_class, standing FROM agent_workers WHERE agent_slug = ?",
            (prepared.slug,),
        )
    finally:
        conn.close()
    assert worker == {"employment_class": "employee", "standing": "active"}


@pytest.mark.parametrize(
    ("historical_employment", "historical_enabled"),
    [("contractor", True), ("disabled", False)],
)
def test_agency_contract_validation_overlays_current_worker_lifecycle(
    tmp_path: Path,
    historical_employment: str,
    historical_enabled: bool,
) -> None:
    store, _canonical, _current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        lineage = _one(
            conn,
            "SELECT recruitment_contract FROM agent_version_lineage WHERE agent_version_id = ?",
            (prepared.target_revision_id,),
        )
        target_revision = _one(
            conn,
            "SELECT * FROM agent_versions WHERE id = ?",
            (prepared.target_revision_id,),
        )
        worker = _one(
            conn,
            "SELECT * FROM agent_workers WHERE agent_slug = ?",
            (prepared.slug,),
        )
    finally:
        conn.close()
    historical = json.loads(str(lineage["recruitment_contract"]))
    historical["origin"] = "agency"
    historical["employment"] = historical_employment
    historical["enabled"] = historical_enabled
    document = json.dumps(historical, sort_keys=True, separators=(",", ":"))
    worker["origin"] = "agency"
    worker["employment_class"] = "employee"

    roster_subject._validate_rollback_contract(
        {
            "recruitment_contract": document,
            "recruitment_contract_hash": content_digest(document),
        },
        slug=prepared.slug,
        worker_id=str(worker["worker_id"]),
        target_revision=target_revision,
        worker=worker,
        source="lineage",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_hash", "0" * 64),
        ("current_projection_digest", "1" * 64),
        ("activation_authority_digest", "2" * 64),
    ],
)
def test_commit_rejects_forged_prepared_binding(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    forged = prepared._replace(**{field: value})
    before = _effect_snapshot(store, prepared.slug)

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, forged)

    assert _effect_snapshot(store, prepared.slug) == before
    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_rejects_activation_authority_drift(tmp_path: Path) -> None:
    store, _first, second, first_candidate_id, prepared = _prepared_candidate_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute(
            "DELETE FROM agent_candidate_status_events "
            "WHERE candidate_id = ? AND event_type = 'approved'",
            (first_candidate_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="activation authority"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == second["version"]


def test_commit_rejects_workforce_identity_drift(tmp_path: Path) -> None:
    store, _canonical_agent, current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_workers SET display_name = display_name || ' drift' WHERE agent_slug = ?",
            (prepared.slug,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="prepared rollback state changed"):
        _commit(store, prepared)

    assert store.get_roster_entry(prepared.slug)["version"] == current["version"]


def test_commit_applies_exact_active_workforce_event_and_generation_once(tmp_path: Path) -> None:
    store, canonical, _current, prepared = _prepared_bundle_target(tmp_path)
    conn = store._connect()
    try:
        before_worker = _one(
            conn,
            "SELECT * FROM agent_workers WHERE agent_slug = ?",
            (prepared.slug,),
        )
        before_event_count = _one(
            conn,
            "SELECT COUNT(*) AS count FROM agent_import_events "
            "WHERE event_type = 'agent_revision_rolled_back' AND agent_slug = ?",
            (prepared.slug,),
        )["count"]
        before_worker_event_count = _one(
            conn,
            "SELECT COUNT(*) AS count FROM agent_worker_events WHERE worker_id = ?",
            (before_worker["worker_id"],),
        )["count"]
    finally:
        conn.close()

    restored = _commit(store, prepared)

    assert restored["version"] == canonical["version"]
    assert restored["hash"] == canonical["hash"]
    assert restored["description"] == canonical["description"]
    assert restored["categories"] == canonical["categories"]
    assert store.get_roster_generation() == prepared.roster_generation + 1
    conn = store._connect()
    try:
        worker = _one(
            conn,
            "SELECT * FROM agent_workers WHERE agent_slug = ?",
            (prepared.slug,),
        )
        target = _one(
            conn,
            "SELECT id FROM agent_versions WHERE agent_slug = ? AND version = ?",
            (prepared.slug, prepared.target_version),
        )
        events = conn.execute(
            "SELECT detail FROM agent_import_events "
            "WHERE event_type = 'agent_revision_rolled_back' AND agent_slug = ?",
            (prepared.slug,),
        ).fetchall()
        worker_event_count = _one(
            conn,
            "SELECT COUNT(*) AS count FROM agent_worker_events WHERE worker_id = ?",
            (worker["worker_id"],),
        )["count"]
    finally:
        conn.close()
    assert worker["current_agent_version_id"] == target["id"]
    assert worker["current_version"] == prepared.target_version
    assert worker["current_hash"] == prepared.target_hash
    assert worker["revision"] == before_worker["revision"] + 1
    assert len(events) == before_event_count + 1
    event_detail = json.loads(events[-1]["detail"])
    assert event_detail == {
        "activation_authority_digest": prepared.activation_authority_digest,
        "activation_authority_kind": prepared.activation_authority_kind,
        "from_hash": prepared.current_hash,
        "from_version": prepared.current_version,
        "target_revision_id": prepared.target_revision_id,
        "to_hash": prepared.target_hash,
        "to_version": prepared.target_version,
        "workforce_identity_digest": prepared.workforce_identity_digest,
    }
    assert {"nonce", "receipt", "stdout", "result"}.isdisjoint(event_detail)
    assert worker_event_count == before_worker_event_count + 1


def test_prepared_rollback_cannot_be_replayed(tmp_path: Path) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    _commit(store, prepared)
    after_first = _effect_snapshot(store, prepared.slug)

    with pytest.raises(ValueError, match="active revision changed"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == after_first


def test_apply_failure_rolls_back_every_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _canonical_agent, _current, prepared = _prepared_bundle_target(tmp_path)
    before = _effect_snapshot(store, prepared.slug)
    apply = roster_subject._apply_agent_revision_rollback_from_connection

    def fail_after_apply(*args: object, **kwargs: object) -> dict[str, Any]:
        apply(*args, **kwargs)
        raise RuntimeError("injected rollback apply failure")

    monkeypatch.setattr(
        roster_subject,
        "_apply_agent_revision_rollback_from_connection",
        fail_after_apply,
    )

    with pytest.raises(RuntimeError, match="injected rollback apply failure"):
        _commit(store, prepared)

    assert _effect_snapshot(store, prepared.slug) == before


def test_snapshot_authority_projection_is_complete_and_deterministic(tmp_path: Path) -> None:
    store, first, _second, _candidate_id, _prepared = _prepared_candidate_target(tmp_path)
    conn = store._connect()
    try:
        revision = _one(
            conn,
            "SELECT * FROM agent_versions WHERE agent_slug = ? AND version = ?",
            (first["agent_slug"], first["version"]),
        )
        first_authority = roster_subject.assert_revision_activation_authority(
            conn,
            slug=first["agent_slug"],
            revision=revision,
        )
        second_authority = roster_subject.assert_revision_activation_authority(
            conn,
            slug=first["agent_slug"],
            revision=revision,
        )
    finally:
        conn.close()
    keys = set(dict(first_authority.projection))
    assert first_authority == second_authority
    assert first_authority.kind == "snapshot"
    assert {
        "candidate_record_digest",
        "candidate_approved_audit_digest",
        "candidate_activated_audit_digest",
        "candidate_approved_event_digest",
        "candidate_activated_event_digest",
        "snapshot_record_digest",
        "snapshot_approved_event_digest",
        "snapshot_activated_event_digest",
    } <= keys
