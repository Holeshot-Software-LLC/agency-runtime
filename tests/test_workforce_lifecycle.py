from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

import pytest

from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.schema import SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce import project_workforce_contract, stable_worker_id
from agency_runtime.core.workforce.known_installer import install_known_contractors


def _agent(slug: str) -> dict[str, object]:
    return next(dict(agent) for agent in BundledRoster() if agent["slug"] == slug)


def _contract_document(value: dict[str, object]) -> tuple[dict[str, object], str]:
    document = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value, hashlib.sha256(document.encode("utf-8")).hexdigest()


def _version_id(store: Store, slug: str) -> str:
    with closing(store._connect()) as conn:
        row = conn.execute(
            "SELECT id FROM agent_versions WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
    assert row is not None
    return str(row["id"])


def _roster_generation(store: Store) -> int:
    with closing(store._connect()) as conn:
        row = conn.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
    assert row is not None
    return int(row["value"])


def _current_lineage(store: Store, slug: str) -> dict[str, object]:
    with closing(store._connect()) as conn:
        row = conn.execute(
            "SELECT lineage.* FROM agent_version_lineage AS lineage "
            "JOIN agent_workers AS worker ON worker.worker_id = lineage.worker_id "
            "AND worker.current_agent_version_id = lineage.agent_version_id "
            "WHERE worker.agent_slug = ?",
            (slug,),
        ).fetchone()
    assert row is not None
    return dict(row)


def _insert_contract_projection(
    store: Store,
    slug: str,
    contract: dict[str, object],
    *,
    contract_hash: str | None = None,
) -> None:
    document = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    lineage = _current_lineage(store, slug)
    with closing(store._connect()) as conn:
        worker = conn.execute(
            "SELECT worker_id, current_agent_version_id FROM agent_workers WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
        assert worker is not None
        sequence = int(
            conn.execute(
                "SELECT COALESCE(MAX(projection_sequence), 0) + 1 "
                "FROM agent_recruitment_contract_projections"
            ).fetchone()[0]
        )
        conn.execute(
            "INSERT INTO agent_recruitment_contract_projections "
            "(id, projection_sequence, worker_id, agent_version_id, "
            "parent_contract_hash, recruitment_contract, recruitment_contract_hash, "
            "projection_authority, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'test-fixture', "
            "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (
                str(uuid.uuid4()),
                sequence,
                worker["worker_id"],
                worker["current_agent_version_id"],
                lineage["recruitment_contract_hash"],
                document,
                contract_hash or hashlib.sha256(document.encode("utf-8")).hexdigest(),
            ),
        )
        conn.commit()


def _agency_contractor(slug: str = "typescript-application-engineer-test") -> dict[str, object]:
    source = _agent("senior-developer")
    return {
        **source,
        "slug": slug,
        "display_name": "TypeScript Application Engineer Test",
        "origin": "agency",
        "employment": "contractor",
        "enabled": True,
    }


def test_packaged_contract_reconciliation_repairs_only_derived_projection(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agent("code-reviewer")
    store.activate_agent(agent)
    version_id = _version_id(store, "code-reviewer")
    with closing(store._connect()) as conn:
        immutable_before = dict(
            conn.execute("SELECT * FROM agent_versions WHERE id = ?", (version_id,)).fetchone()
        )
    lineage = _current_lineage(store, "code-reviewer")
    stale = json.loads(str(lineage["recruitment_contract"]))
    stale["domains"] = ["software-engineering"]
    _insert_contract_projection(store, "code-reviewer", stale)
    generation = _roster_generation(store)

    result = store.reconcile_packaged_workforce_contracts()

    assert result.inspected == 1
    assert result.updated == 1
    assert _roster_generation(store) == generation + 1
    with closing(store._connect()) as conn:
        projection = conn.execute(
            "SELECT recruitment_contract "
            "FROM agent_recruitment_contract_projections "
            "ORDER BY projection_sequence DESC LIMIT 1"
        ).fetchone()
    assert projection is not None
    assert json.loads(str(projection["recruitment_contract"]))["domains"] == [
        "software-engineering",
        "security",
    ]
    with closing(store._connect()) as conn:
        immutable_after = dict(
            conn.execute("SELECT * FROM agent_versions WHERE id = ?", (version_id,)).fetchone()
        )
    assert immutable_after == immutable_before

    second = store.reconcile_packaged_workforce_contracts()

    assert second.inspected == 1
    assert second.updated == 0
    assert _roster_generation(store) == generation + 1


def test_packaged_contract_reconciliation_preserves_repeated_a_b_a_history(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.activate_agent(_agent("code-reviewer"))
    lineage = _current_lineage(store, "code-reviewer")
    original = json.loads(str(lineage["recruitment_contract"]))
    stale = {**original, "domains": ["software-engineering"]}
    stale_document = json.dumps(
        stale,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    stale_hash = hashlib.sha256(stale_document.encode("utf-8")).hexdigest()
    original_hash = str(lineage["recruitment_contract_hash"])
    generation = _roster_generation(store)

    _insert_contract_projection(store, "code-reviewer", stale)
    first_restore = store.reconcile_packaged_workforce_contracts()
    _insert_contract_projection(store, "code-reviewer", stale)
    second_restore = store.reconcile_packaged_workforce_contracts()

    assert first_restore.updated == 1
    assert second_restore.updated == 1
    assert _roster_generation(store) == generation + 2
    with closing(store._connect()) as conn:
        hashes = [
            str(row["recruitment_contract_hash"])
            for row in conn.execute(
                "SELECT recruitment_contract_hash "
                "FROM agent_recruitment_contract_projections "
                "ORDER BY projection_sequence"
            ).fetchall()
        ]
    assert hashes == [stale_hash, original_hash, stale_hash, original_hash]
    assert store.reconcile_packaged_workforce_contracts().updated == 0


def test_schema_upgrade_removes_projection_content_uniqueness_without_losing_history(
    tmp_path: Path,
) -> None:
    database = tmp_path / "agency.db"
    store = Store(database)
    store.activate_agent(_agent("code-reviewer"))
    lineage = _current_lineage(store, "code-reviewer")
    stale = json.loads(str(lineage["recruitment_contract"]))
    stale["domains"] = ["software-engineering"]
    _insert_contract_projection(store, "code-reviewer", stale)
    with closing(store._connect()) as conn:
        original = dict(
            conn.execute("SELECT * FROM agent_recruitment_contract_projections").fetchone()
        )
        conn.execute("DROP TRIGGER agency_contract_projections_immutable_update")
        conn.execute("DROP TRIGGER agency_contract_projections_immutable_delete")
        conn.execute("DROP INDEX idx_agent_contract_projections_worker_sequence")
        conn.execute(
            "ALTER TABLE agent_recruitment_contract_projections "
            "RENAME TO agent_recruitment_contract_projections_current"
        )
        conn.execute(
            "CREATE TABLE agent_recruitment_contract_projections ("
            "id TEXT PRIMARY KEY, "
            "projection_sequence INTEGER NOT NULL UNIQUE CHECK (projection_sequence > 0), "
            "worker_id TEXT NOT NULL, agent_version_id TEXT NOT NULL, "
            "parent_contract_hash TEXT NOT NULL, recruitment_contract TEXT NOT NULL, "
            "recruitment_contract_hash TEXT NOT NULL, projection_authority TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "UNIQUE (worker_id, agent_version_id, recruitment_contract_hash), "
            "FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id), "
            "FOREIGN KEY (agent_version_id) REFERENCES agent_versions(id))"
        )
        columns = ", ".join(original)
        conn.execute(
            "INSERT INTO agent_recruitment_contract_projections "
            f"({columns}) SELECT {columns} "
            "FROM agent_recruitment_contract_projections_current"
        )
        conn.execute("DROP TABLE agent_recruitment_contract_projections_current")
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (34)")
        conn.commit()

    migrated = Store(database)

    with closing(migrated._connect()) as conn:
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        table_sql = str(
            conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' "
                "AND name = 'agent_recruitment_contract_projections'"
            ).fetchone()[0]
        )
        restored = dict(
            conn.execute("SELECT * FROM agent_recruitment_contract_projections").fetchone()
        )
    assert version == SCHEMA_VERSION
    assert "UNIQUE (worker_id, agent_version_id, recruitment_contract_hash)" not in table_sql
    assert restored == original


def test_packaged_contract_reconciliation_skips_unproven_revision(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.activate_agent(_agent("code-reviewer"))
    lineage = _current_lineage(store, "code-reviewer")
    before = str(lineage["recruitment_contract"])
    generation = _roster_generation(store)
    with closing(store._connect()) as conn:
        conn.execute(
            "UPDATE agent_versions SET metadata = '{}' WHERE id = ?",
            (_version_id(store, "code-reviewer"),),
        )
        conn.commit()

    result = store.reconcile_packaged_workforce_contracts()

    assert result.inspected == 0
    assert result.updated == 0
    assert str(_current_lineage(store, "code-reviewer")["recruitment_contract"]) == before
    assert _roster_generation(store) == generation


def test_packaged_contract_reconciliation_rejects_tampered_contract(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.activate_agent(_agent("code-reviewer"))
    lineage = _current_lineage(store, "code-reviewer")
    _insert_contract_projection(
        store,
        "code-reviewer",
        {},
        contract_hash=str(lineage["recruitment_contract_hash"]),
    )

    with pytest.raises(RuntimeError, match="contract hash is invalid"):
        store.reconcile_packaged_workforce_contracts()


def _audited_hiring_case(store: Store, agent: dict[str, object]) -> tuple[dict, dict]:
    contract = project_workforce_contract(agent, origin="agency").to_dict()
    contract, contract_hash = _contract_document(contract)
    case = store.create_hiring_case(
        case_type="hire",
        proposed_slug=str(agent["slug"]),
        work_unit_id=str(uuid.uuid4()),
        request_hash="a" * 64,
        gap_evidence={"missing": ["typescript application delivery"]},
        duplicate_evidence={"nearest": [{"slug": "senior-developer", "insufficient": True}]},
        contract_evidence=contract,
        critic_evidence={
            "approved": True,
            "receipt": {"receipt_id": "critic-receipt", "actual_model": "gpt-test"},
        },
        model_evidence={
            "receipts": [
                {
                    "receipt_id": "hiring-receipt",
                    "provider": "codex-oauth",
                    "actual_model": "gpt-test",
                    "model_receipt_source": "response.body.model",
                }
            ]
        },
        contract_hash=contract_hash,
    )
    return store.transition_hiring_case(case["id"], status="audited"), contract


def test_hiring_registration_consumes_exact_case_and_preserves_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agency_contractor()
    version_id = store.stage_agency_workforce_agent(agent)
    assert store.get_specialist_prompt(str(agent["slug"]), disabled_agents=()) is None
    case, contract = _audited_hiring_case(store, agent)

    worker = store.register_workforce_worker(
        agent_slug=str(agent["slug"]),
        display_name=str(agent["display_name"]),
        origin="agency",
        employment_class="contractor",
        agent_version_id=version_id,
        recruitment_contract=contract,
        relation="generated",
        hiring_case_id=case["id"],
    )

    assert worker["worker_id"] == stable_worker_id(agent["slug"])
    assert worker["state"] == "contractor"
    assert worker["display_label"].startswith("Contractor · ")
    assert store.get_hiring_case(case["id"])["status"] == "applied"
    with pytest.raises(ValueError, match=r"already exists|audited"):
        store.register_workforce_worker(
            agent_slug=str(agent["slug"]),
            display_name=str(agent["display_name"]),
            origin="agency",
            employment_class="contractor",
            agent_version_id=version_id,
            recruitment_contract=contract,
            relation="generated",
            hiring_case_id=case["id"],
        )


def test_operator_evidence_queries_return_bounded_decoded_lifecycle_history(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agency_contractor("evidence-query-contractor")
    version_id = store.stage_agency_workforce_agent(agent)
    case, contract = _audited_hiring_case(store, agent)
    worker = store.register_workforce_worker(
        agent_slug=str(agent["slug"]),
        display_name=str(agent["display_name"]),
        origin="agency",
        employment_class="contractor",
        agent_version_id=version_id,
        recruitment_contract=contract,
        relation="generated",
        hiring_case_id=case["id"],
    )

    cases = store.list_hiring_cases(status="applied", case_type="hire", limit=10)
    detail = store.get_workforce_worker_detail(worker["worker_id"], evidence_limit=10)

    assert [item["id"] for item in cases] == [case["id"]]
    assert cases[0]["gap_evidence"] == {"missing": ["typescript application delivery"]}
    assert detail["worker"]["worker_id"] == worker["worker_id"]
    assert detail["recruitment_contract"]["worker_id"] == worker["worker_id"]
    assert detail["lineage"][0]["relation"] == "generated"
    assert detail["events"][0]["event_type"] == "registered"
    assert detail["events"][0]["evidence"] == {}
    assert detail["outcomes"] == []
    assert [item["id"] for item in detail["hiring_cases"]] == [case["id"]]

    with pytest.raises(ValueError, match="status"):
        store.list_hiring_cases(status="unknown")
    with pytest.raises(ValueError, match="evidence limit"):
        store.get_workforce_worker_detail(worker["worker_id"], evidence_limit=0)


def test_promotion_and_disable_overlay_keep_contractor_history(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agency_contractor()
    version_id = store.stage_agency_workforce_agent(agent)
    case, contract = _audited_hiring_case(store, agent)
    contractor = store.register_workforce_worker(
        agent_slug=str(agent["slug"]),
        display_name=str(agent["display_name"]),
        origin="agency",
        employment_class="contractor",
        agent_version_id=version_id,
        recruitment_contract=contract,
        relation="generated",
        hiring_case_id=case["id"],
    )

    disabled = store.get_workforce_worker(
        contractor["worker_id"],
        disabled_agents={str(agent["slug"])},
    )
    assert disabled["state"] == "disabled"
    assert disabled["enabled"] is False
    assert disabled["display_label"].startswith("Contractor · ")

    promoted = store.transition_workforce_worker(
        contractor["worker_id"],
        action="promote",
        expected_revision=0,
        reason="independently verified successful assignments",
    )
    assert promoted["worker_id"] == contractor["worker_id"]
    assert promoted["agent_slug"] == contractor["agent_slug"]
    assert promoted["current_version"] == contractor["current_version"]
    assert promoted["current_hash"] == contractor["current_hash"]
    assert promoted["state"] == "employee"
    assert not promoted["display_label"].startswith("Contractor · ")

    suspended = store.transition_workforce_worker(
        promoted["worker_id"],
        action="suspend",
        expected_revision=1,
        reason="operator safety hold",
    )
    assert suspended["state"] == "suspended"
    assert store.get_specialist_prompt(str(agent["slug"]), disabled_agents=()) is None
    assert str(agent["slug"]) not in {
        row["slug"] for row in store.get_routing_roster_snapshot()["catalog"]
    }
    resumed = store.transition_workforce_worker(
        suspended["worker_id"],
        action="resume",
        expected_revision=2,
        reason="hold cleared",
    )
    assert resumed["state"] == "employee"
    assert store.get_specialist_prompt(str(agent["slug"]), disabled_agents=()) is not None


def test_hiring_evidence_is_idempotent_proof_gated_and_immutable(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agency_contractor()
    contract = project_workforce_contract(agent, origin="agency").to_dict()
    contract, contract_hash = _contract_document(contract)
    kwargs = {
        "case_type": "hire",
        "proposed_slug": str(agent["slug"]),
        "work_unit_id": str(uuid.uuid4()),
        "request_hash": "b" * 64,
        "gap_evidence": {"missing": ["typescript"]},
        "duplicate_evidence": {"nearest": []},
        "contract_evidence": contract,
        "critic_evidence": {"approved": False, "receipt": {"receipt_id": "critic"}},
        "model_evidence": {
            "receipts": [
                {
                    "receipt_id": "hire",
                    "provider": "codex-oauth",
                    "actual_model": "gpt-test",
                    "model_receipt_source": "response.body.model",
                }
            ]
        },
        "contract_hash": contract_hash,
    }
    first = store.create_hiring_case(**kwargs)
    assert store.create_hiring_case(**kwargs)["id"] == first["id"]
    with pytest.raises(ValueError, match="critic"):
        store.transition_hiring_case(first["id"], status="audited")

    with (
        closing(store._connect()) as conn,
        pytest.raises(sqlite3.IntegrityError, match="immutable"),
    ):
        conn.execute("DELETE FROM agent_hiring_cases WHERE id = ?", (first["id"],))


def test_high_risk_hiring_requires_explicit_operator_approval(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agency_contractor("security-offensive-contractor-test")
    contract = project_workforce_contract(agent, origin="agency").to_dict()
    contract, contract_hash = _contract_document(contract)
    case = store.create_hiring_case(
        case_type="hire",
        proposed_slug=str(agent["slug"]),
        work_unit_id=str(uuid.uuid4()),
        request_hash="c" * 64,
        gap_evidence={"missing": ["authorized offensive security"]},
        duplicate_evidence={"nearest": []},
        contract_evidence=contract,
        critic_evidence={"approved": True, "receipt": {"receipt_id": "critic"}},
        model_evidence={
            "receipts": [
                {
                    "receipt_id": "hire",
                    "provider": "codex-oauth",
                    "actual_model": "gpt-test",
                    "model_receipt_source": "response.body.model",
                }
            ]
        },
        contract_hash=contract_hash,
        risk_tier="high",
        human_approval_required=True,
    )
    with pytest.raises(ValueError, match="human approval"):
        store.transition_hiring_case(case["id"], status="audited")
    approved = store.approve_hiring_case(case["id"], approved_by="operator@example.test")
    assert approved["human_approved_at"]
    assert store.transition_hiring_case(case["id"], status="audited")["status"] == "audited"


def test_every_bundled_agent_bootstraps_one_worker_and_lineage_record(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agents = [dict(agent) for agent in BundledRoster()]

    assert store.activate_agents_if_missing(agents) == 263
    assert store.count_active_roster() == 263
    with closing(store._connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_workers").fetchone()[0] == 263
        assert conn.execute("SELECT COUNT(*) FROM agent_version_lineage").fetchone()[0] == 263
        assert (
            conn.execute(
                "SELECT COUNT(DISTINCT current_agent_version_id) FROM agent_workers"
            ).fetchone()[0]
            == 263
        )
    snapshot = workforce_index_snapshot(store, disabled_agents={"code-reviewer"})
    assert snapshot.worker_count == 263
    assert snapshot.contract_fingerprint.startswith("sha256:")
    assert snapshot.recruiter_fingerprint.startswith("sha256:")
    assert len(snapshot.recruiter_index.encode("utf-8")) <= 256 * 1024
    disabled = next(item for item in snapshot.contracts if item.agent_id == "code-reviewer")
    assert disabled.enabled is False
    assert disabled.employment == "disabled"
    assert len(disabled.version_hash) == 64


def test_v32_upgrade_backfills_existing_active_workforce_identity(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    with closing(store._connect()) as conn, conn:
        for trigger in (
            "agency_version_lineage_immutable_delete",
            "agency_worker_events_immutable_delete",
            "agency_workers_immutable_delete",
        ):
            conn.execute(f"DROP TRIGGER {trigger}")
        conn.execute("DELETE FROM agent_version_lineage")
        conn.execute("DELETE FROM agent_worker_events")
        conn.execute("DELETE FROM agent_workers")
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version(version) VALUES (32)")

    upgraded = Store(path)
    worker = upgraded.get_workforce_worker("code-reviewer", disabled_agents=())
    assert worker["worker_id"] == stable_worker_id("code-reviewer")
    assert worker["state"] == "employee"
    assert upgraded.get_specialist_prompt("code-reviewer", disabled_agents=()) is not None


def test_audited_amendment_preserves_worker_and_upstream_version_history(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    source = _agent("code-reviewer")
    store._activate_prevalidated_agent(source)
    before = store.get_workforce_worker("code-reviewer", disabled_agents=())
    amended = {
        **source,
        "origin": "agency",
        "employment": "employee",
        "enabled": True,
        "version": "agency-amendment-test-v2",
        "prompt_body": str(source["prompt_body"])
        + "\n\nAgency amendment: review cross-platform packaging evidence.",
    }
    amended.pop("hash", None)
    amended["version_hash"] = hashlib.sha256(
        str(amended["prompt_body"]).encode("utf-8")
    ).hexdigest()
    version_id = store.stage_agency_workforce_amendment(amended, expected_revision=0)
    contract = project_workforce_contract(amended, origin="agency").to_dict()
    contract, contract_hash = _contract_document(contract)
    case = store.create_hiring_case(
        case_type="amend",
        proposed_slug="code-reviewer",
        target_worker_id=before["worker_id"],
        work_unit_id=str(uuid.uuid4()),
        request_hash="d" * 64,
        gap_evidence={"missing": ["cross-platform packaging review"]},
        duplicate_evidence={
            "fold_into": "code-reviewer",
            "coherent": True,
            "nearest": ["cross-platform-release-verifier"],
        },
        contract_evidence=contract,
        critic_evidence={"approved": True, "receipt": {"receipt_id": "critic"}},
        model_evidence={
            "receipts": [
                {
                    "receipt_id": "amend",
                    "provider": "codex-oauth",
                    "actual_model": "gpt-test",
                    "model_receipt_source": "response.body.model",
                }
            ]
        },
        contract_hash=contract_hash,
    )
    audited = store.transition_hiring_case(case["id"], status="audited")
    after = store.apply_workforce_amendment(
        before["worker_id"],
        expected_revision=0,
        agent_version_id=version_id,
        recruitment_contract=contract,
        hiring_case_id=audited["id"],
    )

    assert after["worker_id"] == before["worker_id"]
    assert after["agent_slug"] == before["agent_slug"]
    assert after["current_version"] == "agency-amendment-test-v2"
    assert store.get_hiring_case(case["id"])["status"] == "applied"
    prompt = store.get_specialist_prompt("code-reviewer", disabled_agents=())
    assert prompt is not None
    assert "cross-platform packaging evidence" in prompt["prompt_body"]
    with closing(store._connect()) as conn:
        relations = [
            row[0]
            for row in conn.execute(
                "SELECT relation FROM agent_version_lineage WHERE worker_id = ? "
                "ORDER BY created_at, rowid",
                (before["worker_id"],),
            )
        ]
    assert relations == ["generated", "agency_amendment"]


def test_performance_outcomes_bind_consumed_activation_and_replay_safely(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    worker = store.get_workforce_worker("code-reviewer", disabled_agents=())
    store.create_run(trace_id="workforce-trace", session_id="workforce-session", host="codex")
    with closing(store._connect()) as conn, conn:
        conn.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "('workforce-activation', ?, 'workforce-session', 'workforce-trace', "
            "'unit-review', 'code-reviewer', ?, ?, 'native-child', 'child-1', "
            "'codex:child-1', '2026-07-21T00:00:00+00:00', "
            "'2026-07-21T00:00:01+00:00')",
            ("e" * 64, worker["current_version"], worker["current_hash"]),
        )

    first = store.record_workforce_outcome(
        worker["worker_id"],
        idempotency_key="f" * 64,
        event_type="review",
        outcome="passed",
        score=1.0,
        evidence_hash="a" * 64,
        evidence_refs={"artifact": "git-diff:abc123"},
        activation_receipt_id="workforce-activation",
    )
    replay = store.record_workforce_outcome(
        worker["worker_id"],
        idempotency_key="f" * 64,
        event_type="review",
        outcome="passed",
        score=1.0,
        evidence_hash="a" * 64,
        evidence_refs={"artifact": "git-diff:abc123"},
        activation_receipt_id="workforce-activation",
    )
    assert replay == first
    assert first["version"] == worker["current_version"]
    assert first["trace_id"] == "workforce-trace"
    assert first["evidence_refs"] == {"artifact": "git-diff:abc123"}

    with pytest.raises(ValueError, match="different evidence"):
        store.record_workforce_outcome(
            worker["worker_id"],
            idempotency_key="f" * 64,
            event_type="review",
            outcome="failed",
            evidence_hash="b" * 64,
            evidence_refs={"artifact": "git-diff:different"},
            activation_receipt_id="workforce-activation",
        )
    with (
        closing(store._connect()) as conn,
        pytest.raises(sqlite3.IntegrityError, match="immutable"),
    ):
        conn.execute(
            "UPDATE agent_performance_events SET outcome = 'tampered' WHERE id = ?",
            (first["id"],),
        )


def test_receipt_validated_acceptance_can_auto_promote_without_changing_identity(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    contractor = store.get_workforce_worker(
        "typescript-application-engineer",
        disabled_agents=(),
    )
    verifier = store.get_workforce_worker("code-reviewer", disabled_agents=())
    store.create_run(trace_id="promotion-trace", session_id="promotion-session", host="codex")
    with closing(store._connect()) as conn, conn:
        conn.executemany(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "(?, ?, 'promotion-session', 'promotion-trace', ?, ?, ?, ?, "
            "'native-child', ?, ?, '2026-07-21T00:00:00+00:00', "
            "'2026-07-21T00:00:01+00:00')",
            [
                (
                    "contractor-activation",
                    "a" * 64,
                    "unit-build",
                    contractor["agent_slug"],
                    contractor["current_version"],
                    contractor["current_hash"],
                    "child-build",
                    "codex:child-build",
                ),
                (
                    "verifier-activation",
                    "b" * 64,
                    "unit-review",
                    verifier["agent_slug"],
                    verifier["current_version"],
                    verifier["current_hash"],
                    "child-review",
                    "codex:child-review",
                ),
            ],
        )

    recorded = store.record_workforce_outcome(
        contractor["worker_id"],
        idempotency_key="c" * 64,
        event_type="acceptance",
        outcome="passed",
        score=1.0,
        evidence_hash="d" * 64,
        evidence_refs={
            "artifact": "git-diff:complete-app",
            "independent_verifier_worker_id": verifier["worker_id"],
            "independent_verification_receipt_id": "verifier-activation",
        },
        activation_receipt_id="contractor-activation",
        auto_promote_successes=1,
        disabled_agents=(),
    )

    after = store.get_workforce_worker_detail(
        contractor["worker_id"],
        disabled_agents=(),
    )
    assert recorded["evidence_refs"]["independent_verification_validated"] is True
    assert after["worker"]["worker_id"] == contractor["worker_id"]
    assert after["worker"]["agent_slug"] == contractor["agent_slug"]
    assert after["worker"]["state"] == "employee"
    assert not after["worker"]["display_label"].startswith("Contractor · ")
    promotion = next(item for item in after["events"] if item["event_type"] == "promote")
    assert promotion["actor"] == "promotion-policy"
    assert promotion["evidence"]["verified_work_units"] == ["unit-build"]


def test_acceptance_rejects_unproven_independent_verifier_receipts(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    contractor = store.get_workforce_worker(
        "typescript-application-engineer",
        disabled_agents=(),
    )
    store.create_run(trace_id="invalid-trace", session_id="invalid-session", host="codex")
    with closing(store._connect()) as conn, conn:
        conn.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "('source-activation', ?, 'invalid-session', 'invalid-trace', "
            "'unit-build', ?, ?, ?, 'native-child', 'child-build', "
            "'codex:child-build', '2026-07-21T00:00:00+00:00', "
            "'2026-07-21T00:00:01+00:00')",
            (
                "e" * 64,
                contractor["agent_slug"],
                contractor["current_version"],
                contractor["current_hash"],
            ),
        )

    with pytest.raises(ValueError, match="missing or unconsumed"):
        store.record_workforce_outcome(
            contractor["worker_id"],
            idempotency_key="f" * 64,
            event_type="acceptance",
            outcome="passed",
            evidence_hash="0" * 64,
            evidence_refs={
                "independent_verifier_worker_id": "worker-does-not-exist",
                "independent_verification_receipt_id": "missing-receipt",
            },
            activation_receipt_id="source-activation",
            auto_promote_successes=1,
            disabled_agents=(),
        )


def test_merge_and_state_pages_preserve_history_and_exclude_routing(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    store._activate_prevalidated_agent(_agent("reality-checker"))
    source = store.get_workforce_worker("code-reviewer", disabled_agents=())
    target = store.get_workforce_worker("reality-checker", disabled_agents=())

    with pytest.raises(ValueError, match="merge target"):
        store.transition_workforce_worker(
            source["worker_id"],
            action="merge",
            expected_revision=0,
            reason="invalid self merge",
            merged_into_worker_id=source["worker_id"],
        )
    merged = store.transition_workforce_worker(
        source["worker_id"],
        action="merge",
        expected_revision=0,
        reason="capability was coherently superseded",
        merged_into_worker_id=target["agent_slug"],
    )
    assert merged["state"] == "merged"
    assert merged["merged_into_worker_id"] == target["worker_id"]
    assert store.get_specialist_prompt("code-reviewer", disabled_agents=()) is None
    assert store.get_specialist_prompt("reality-checker", disabled_agents=()) is not None
    assert (
        store.list_workforce_workers(
            state="merged",
            limit=1,
            disabled_agents=(),
        )[0]["worker_id"]
        == source["worker_id"]
    )

    with (
        closing(store._connect()) as conn,
        pytest.raises(sqlite3.IntegrityError, match="immutable"),
    ):
        conn.execute(
            "DELETE FROM agent_worker_events WHERE worker_id = ?",
            (source["worker_id"],),
        )
    with pytest.raises(RuntimeError, match="revision conflict"):
        store.transition_workforce_worker(
            target["worker_id"],
            action="suspend",
            expected_revision=99,
            reason="stale operator view",
        )


def test_disabled_contractors_cannot_promote_or_receive_merges(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    source = store.get_workforce_worker(
        "typescript-application-engineer",
        disabled_agents=(),
    )
    target = store.get_workforce_worker(
        "python-application-engineer",
        disabled_agents=(),
    )

    with pytest.raises(ValueError, match="enabled before promotion"):
        store.transition_workforce_worker(
            source["worker_id"],
            action="promote",
            expected_revision=0,
            reason="must not bypass activation policy",
            disabled_agents={source["agent_slug"]},
        )
    with pytest.raises(ValueError, match="merge target must be enabled"):
        store.transition_workforce_worker(
            source["worker_id"],
            action="merge",
            expected_revision=0,
            reason="must not merge into unavailable capability",
            merged_into_worker_id=target["agent_slug"],
            disabled_agents={target["agent_slug"]},
        )


def test_enablement_evidence_is_idempotent_and_preserves_worker_revision(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    before = store.get_workforce_worker("code-reviewer", disabled_agents=())

    for _attempt in range(2):
        store.record_workforce_enablement(
            before["worker_id"],
            enabled=False,
            config_revision="a" * 64,
            reason="operator disabled a risky selection",
            surface="dashboard",
        )

    detail = store.get_workforce_worker_detail("code-reviewer", disabled_agents=())
    events = [item for item in detail["events"] if item["event_type"] == "disable"]
    assert len(events) == 1
    assert events[0]["reason"] == "operator disabled a risky selection"
    assert events[0]["evidence"] == {
        "config_revision": "a" * 64,
        "enabled": False,
    }
    assert detail["worker"]["revision"] == before["revision"]
