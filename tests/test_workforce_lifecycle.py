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
from agency_runtime.core.store.workforce import (
    MAX_HIRING_COLLECTION_RESPONSE_BYTES,
    MAX_HIRING_SUMMARY_PAGE,
    MAX_WORKFORCE_DOCUMENT_BYTES,
)
from agency_runtime.core.workforce import project_workforce_contract, stable_worker_id
from agency_runtime.core.workforce.acceptance import (
    ACCEPTANCE_ENVELOPE_SCHEMA,
    HOST_CHILD_PROOF_SCHEMA,
)
from agency_runtime.core.workforce.known_installer import install_known_contractors
from agency_runtime.core.workforce.promotion import promotion_readiness


def _agent(slug: str) -> dict[str, object]:
    return next(dict(agent) for agent in BundledRoster() if agent["slug"] == slug)


def _delivery_proof(worker: dict[str, object], *, child_id: str, decision_id: str) -> dict:
    """One sealed host-child delivery proof for this worker's active card."""

    return {
        "schema": HOST_CHILD_PROOF_SCHEMA,
        "verified_delivery": True,
        "host": "codex",
        "child_id": child_id,
        "decision_id": decision_id,
        "artifact_digest": "",
        "cards": [
            {
                "specialist_slug": str(worker["agent_slug"]),
                "specialist_version": str(worker["current_version"]),
                "specialist_prompt_hash": str(worker["current_hash"]),
            }
        ],
    }


def _acceptance_envelope(
    contractor: dict[str, object],
    verifier: dict[str, object],
    *,
    index: int,
) -> dict[str, object]:
    """A host-evidenced acceptance for one distinct produced artifact (AR-252)."""

    digest = f"{index:064x}"
    verifier_digest = f"{index + 10_000:064x}"
    producer = _delivery_proof(
        contractor,
        child_id=f"child-producer-{index}",
        decision_id="decision-producer",
    )
    producer["artifact_digest"] = digest
    return {
        "schema": ACCEPTANCE_ENVELOPE_SCHEMA,
        "contractor_worker_id": str(contractor["worker_id"]),
        "contractor_card": {
            "specialist_slug": str(contractor["agent_slug"]),
            "specialist_version": str(contractor["current_version"]),
            "specialist_prompt_hash": str(contractor["current_hash"]),
        },
        "producer": producer,
        "verifier": {
            **_delivery_proof(
                verifier,
                child_id="child-verifier",
                decision_id="decision-verifier",
            ),
            "artifact_digest": verifier_digest,
        },
        "verdict": {
            "verdict_id": f"verdict-{index}",
            "semantic": {
                "authority": "verifier-host-artifact",
                "artifact_digest": verifier_digest,
                "record_index": 1,
                "decision": "accepted",
            },
            "binding": {
                "authority": "collector",
                "producer_artifact_digest": digest,
                "verifier_child_id": "child-verifier",
            },
        },
    }


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
        "quality-assurance",
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
    assert cases[0]["evidence_included"] is True
    assert detail["worker"]["worker_id"] == worker["worker_id"]
    assert detail["recruitment_contract"]["worker_id"] == worker["worker_id"]
    assert detail["lineage"][0]["relation"] == "generated"
    assert detail["evidence_limit"] == 10
    assert detail["lineage_total_count"] == 1
    assert detail["lineage_truncated"] is False
    assert detail["events"][0]["event_type"] == "registered"
    assert detail["events"][0]["evidence"] == {}
    assert detail["events_total_count"] == 1
    assert detail["events_truncated"] is False
    assert detail["outcomes"] == []
    assert detail["outcomes_total_count"] == 0
    assert detail["outcomes_truncated"] is False
    assert [item["id"] for item in detail["hiring_cases"]] == [case["id"]]
    assert detail["hiring_cases_total_count"] == 1
    assert detail["hiring_cases_truncated"] is False
    assert set(detail["hiring_cases"][0]) == {
        "id",
        "case_type",
        "status",
        "proposed_slug",
        "target_worker_id",
        "work_unit_id",
        "risk_tier",
        "human_approval_required",
        "human_approved_by",
        "human_approved_at",
        "created_at",
        "decided_at",
        "applied_at",
        "evidence_included",
    }
    assert detail["hiring_cases"][0]["evidence_included"] is False
    exact_case = store.get_hiring_case(case["id"])
    assert exact_case["gap_evidence"] == {"missing": ["typescript application delivery"]}
    assert exact_case["evidence_included"] is True

    with pytest.raises(ValueError, match="status"):
        store.list_hiring_cases(status="unknown")
    with pytest.raises(ValueError, match="evidence limit"):
        store.get_workforce_worker_detail(worker["worker_id"], evidence_limit=0)


def test_worker_detail_filters_hiring_cases_before_applying_evidence_limit(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    target_agent = _agency_contractor("bounded-worker-detail-target")
    target_version_id = store.stage_agency_workforce_agent(target_agent)
    target_case, target_contract = _audited_hiring_case(store, target_agent)
    target_worker = store.register_workforce_worker(
        agent_slug=str(target_agent["slug"]),
        display_name=str(target_agent["display_name"]),
        origin="agency",
        employment_class="contractor",
        agent_version_id=target_version_id,
        recruitment_contract=target_contract,
        relation="generated",
        hiring_case_id=target_case["id"],
    )
    unrelated_case_ids = {
        str(_audited_hiring_case(store, _agency_contractor(f"unrelated-worker-{index}"))[0]["id"])
        for index in range(3)
    }

    detail = store.get_workforce_worker_detail(target_worker["worker_id"], evidence_limit=1)

    assert [item["id"] for item in detail["hiring_cases"]] == [target_case["id"]]
    assert unrelated_case_ids.isdisjoint(item["id"] for item in detail["hiring_cases"])
    assert detail["hiring_cases_total_count"] == 1
    assert detail["hiring_cases_truncated"] is False


def test_worker_detail_caps_lineage_and_reports_exact_total(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    worker = store.get_workforce_worker("code-reviewer", disabled_agents=())
    current_lineage = _current_lineage(store, "code-reviewer")
    parent_version_id = str(current_lineage["agent_version_id"])
    with closing(store._connect()) as conn, conn:
        for index in range(3):
            version_id = f"bounded-lineage-version-{index}"
            version = f"bounded-lineage-v{index}"
            version_hash = hashlib.sha256(version.encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT INTO agent_versions "
                "(id, agent_slug, version, source_version, source_id, hash, content, "
                "metadata, created_at) VALUES (?, 'code-reviewer', ?, '', '', ?, NULL, "
                "'{}', ?)",
                (version_id, version, version_hash, f"2099-01-0{index + 1}T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO agent_version_lineage "
                "(id, worker_id, agent_version_id, parent_version_id, relation, "
                "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
                "VALUES (?, ?, ?, ?, 'agency_amendment', ?, ?, NULL, ?)",
                (
                    f"bounded-lineage-{index}",
                    worker["worker_id"],
                    version_id,
                    parent_version_id,
                    current_lineage["recruitment_contract"],
                    current_lineage["recruitment_contract_hash"],
                    f"2099-01-0{index + 1}T00:00:00Z",
                ),
            )
            parent_version_id = version_id
        conn.execute(
            "INSERT INTO agent_version_lineage "
            "(id, worker_id, agent_version_id, parent_version_id, relation, "
            "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
            "VALUES ('bounded-lineage-orphan', ?, 'missing-agent-version', ?, "
            "'agency_amendment', ?, ?, NULL, '2099-01-04T00:00:00Z')",
            (
                worker["worker_id"],
                parent_version_id,
                current_lineage["recruitment_contract"],
                current_lineage["recruitment_contract_hash"],
            ),
        )

    detail = store.get_workforce_worker_detail(worker["worker_id"], evidence_limit=2)

    assert [item["id"] for item in detail["lineage"]] == [
        "bounded-lineage-2",
        "bounded-lineage-1",
    ]
    assert detail["lineage_total_count"] == 4
    assert detail["lineage_truncated"] is True


def test_worker_detail_projects_worker_and_evidence_from_one_read_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    before = store.get_workforce_worker("code-reviewer", disabled_agents=())
    original_connect = store._connect
    instrumented_connection_issued = False
    mutation_completed = False

    class _CursorAfterWorkerFetch:
        def __init__(self, cursor):
            self._cursor = cursor

        def fetchone(self):
            nonlocal mutation_completed
            row = self._cursor.fetchone()
            if not mutation_completed:
                mutation_completed = True
                store.transition_workforce_worker(
                    before["worker_id"],
                    action="suspend",
                    expected_revision=int(before["revision"]),
                    reason="deterministic concurrent snapshot mutation",
                    disabled_agents=(),
                )
            return row

        def __getattr__(self, name):
            return getattr(self._cursor, name)

    class _ConnectionWithWorkerFetchHook:
        def __init__(self, connection):
            self._connection = connection

        def execute(self, statement, parameters=()):
            cursor = self._connection.execute(statement, parameters)
            if (
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1"
                in statement
            ):
                return _CursorAfterWorkerFetch(cursor)
            return cursor

        def __getattr__(self, name):
            return getattr(self._connection, name)

    def _connect_with_one_hook():
        nonlocal instrumented_connection_issued
        connection = original_connect()
        if instrumented_connection_issued:
            return connection
        instrumented_connection_issued = True
        return _ConnectionWithWorkerFetchHook(connection)

    monkeypatch.setattr(store, "_connect", _connect_with_one_hook)

    detail = store.get_workforce_worker_detail(
        "code-reviewer",
        disabled_agents=(),
        include_history_documents=False,
    )
    after = store.get_workforce_worker("code-reviewer", disabled_agents=())

    assert mutation_completed is True
    assert detail["worker"]["revision"] == before["revision"]
    assert detail["worker"]["standing"] == "active"
    assert all(item["event_type"] != "suspend" for item in detail["events"])
    assert after["revision"] == int(before["revision"]) + 1
    assert after["standing"] == "suspended"


def test_worker_detail_hiring_summary_cannot_embed_full_evidence_documents(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    worker = store.get_workforce_worker("code-reviewer", disabled_agents=())
    large_document = {"payload": "x" * (MAX_WORKFORCE_DOCUMENT_BYTES - 64)}
    contract_document, contract_hash = _contract_document(large_document)
    case = store.create_hiring_case(
        case_type="amend",
        proposed_slug="code-reviewer",
        target_worker_id=worker["worker_id"],
        work_unit_id="bounded-worker-detail-evidence",
        request_hash="a" * 64,
        gap_evidence=large_document,
        duplicate_evidence=large_document,
        contract_evidence=contract_document,
        critic_evidence=large_document,
        model_evidence=large_document,
        contract_hash=contract_hash,
    )

    detail = store.get_workforce_worker_detail(worker["worker_id"], evidence_limit=1)
    summary = detail["hiring_cases"][0]
    serialized_summary = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
    full_case = store.get_hiring_case(case["id"])
    full_evidence_bytes = sum(
        len(json.dumps(full_case[field], sort_keys=True, separators=(",", ":")).encode())
        for field in (
            "gap_evidence",
            "duplicate_evidence",
            "contract_evidence",
            "critic_evidence",
            "model_evidence",
        )
    )

    assert summary["id"] == case["id"]
    assert summary["evidence_included"] is False
    assert not {
        "gap_evidence",
        "duplicate_evidence",
        "contract_evidence",
        "critic_evidence",
        "model_evidence",
    }.intersection(summary)
    assert len(serialized_summary) < 2_048
    assert full_evidence_bytes > 4 * MAX_WORKFORCE_DOCUMENT_BYTES


def test_hiring_collection_snapshot_is_a_bounded_200_row_summary(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    large_document = {"payload": "collection-evidence-" * 13_100}
    exact_case_id = ""
    evidence_fields = {
        "gap_evidence",
        "duplicate_evidence",
        "contract_evidence",
        "critic_evidence",
        "model_evidence",
    }
    for index in range(MAX_HIRING_SUMMARY_PAGE):
        evidence = large_document if index == 0 else {"case": index}
        contract, contract_hash = _contract_document(evidence)
        case = store.create_hiring_case(
            case_type="hire",
            proposed_slug=f"bounded-hire-{index}",
            work_unit_id=f"bounded-hiring-unit-{index}",
            request_hash=hashlib.sha256(f"bounded-hiring-{index}".encode()).hexdigest(),
            gap_evidence=evidence,
            duplicate_evidence=evidence,
            contract_evidence=contract,
            critic_evidence=evidence,
            model_evidence=evidence,
            contract_hash=contract_hash,
        )
        if index == 0:
            exact_case_id = str(case["id"])

    snapshot = store.get_hiring_cases_page_snapshot(limit=MAX_HIRING_SUMMARY_PAGE)
    serialized_snapshot = json.dumps(
        snapshot,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    assert len(snapshot["rows"]) == MAX_HIRING_SUMMARY_PAGE
    assert snapshot["total_count"] == MAX_HIRING_SUMMARY_PAGE
    assert snapshot["filtered_count"] == MAX_HIRING_SUMMARY_PAGE
    assert snapshot["truncated"] is False
    assert len(serialized_snapshot) <= MAX_HIRING_COLLECTION_RESPONSE_BYTES
    assert all(item["evidence_included"] is False for item in snapshot["rows"])
    assert all(not evidence_fields.intersection(item) for item in snapshot["rows"])

    exact_case = store.get_hiring_case(exact_case_id)
    assert exact_case["evidence_included"] is True
    assert all(exact_case[field] == large_document for field in evidence_fields)
    with pytest.raises(ValueError, match="limit"):
        store.get_hiring_cases_page_snapshot(limit=MAX_HIRING_SUMMARY_PAGE + 1)


def test_worker_dashboard_history_projection_omits_documents_and_keeps_proof_scalar(
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
    store.create_run(trace_id="summary-trace", session_id="summary-session", host="codex")
    with closing(store._connect()) as conn, conn:
        conn.executemany(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at) VALUES "
            "(?, ?, 'summary-session', 'summary-trace', ?, ?, ?, ?, "
            "'native-child', ?, ?, '2026-07-26T00:00:00+00:00', "
            "'2026-07-26T00:00:01+00:00')",
            [
                (
                    "summary-contractor-activation",
                    "1" * 64,
                    "summary-unit",
                    contractor["agent_slug"],
                    contractor["current_version"],
                    contractor["current_hash"],
                    "summary-contractor-child",
                    "codex:summary-contractor-child",
                ),
                (
                    "summary-verifier-activation",
                    "2" * 64,
                    "summary-review-unit",
                    verifier["agent_slug"],
                    verifier["current_version"],
                    verifier["current_hash"],
                    "summary-verifier-child",
                    "codex:summary-verifier-child",
                ),
            ],
        )
        event_sequence = int(
            conn.execute(
                "SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM agent_worker_events"
            ).fetchone()[0]
        )
        conn.execute(
            "INSERT INTO agent_worker_events "
            "(id, event_sequence, worker_id, event_type, from_class, to_class, "
            "from_standing, to_standing, version, actor, surface, reason, evidence, "
            "created_at) VALUES (?, ?, ?, 'audit', 'contractor', 'contractor', "
            "'active', 'active', ?, 'test', 'test', 'operator-note-sentinel-private', ?, "
            "'2026-07-26T00:00:02+00:00')",
            (
                str(uuid.uuid4()),
                event_sequence,
                contractor["worker_id"],
                contractor["current_version"],
                json.dumps(
                    {"payload": "private-event-sentinel-" * 10_000},
                    separators=(",", ":"),
                ),
            ),
        )

    outcome = store.record_workforce_outcome(
        contractor["worker_id"],
        idempotency_key="3" * 64,
        event_type="artifact",
        outcome="passed",
        score=1.0,
        evidence_hash="4" * 64,
        evidence_refs={"payload": "private-outcome-sentinel-" * 9_000},
        activation_receipt_id="summary-contractor-activation",
        auto_promote_successes=0,
        disabled_agents=(),
    )
    accepted = store.record_accepted_outcome(
        envelope=_acceptance_envelope(contractor, verifier, index=1),
        auto_promote_successes=0,
        disabled_agents=(),
    )
    full = store.get_workforce_worker_detail(
        contractor["worker_id"],
        evidence_limit=10,
        disabled_agents=(),
    )
    summary = store.get_workforce_worker_detail(
        contractor["worker_id"],
        evidence_limit=10,
        disabled_agents=(),
        include_history_documents=False,
    )

    private_row = next(item for item in full["outcomes"] if item["event_type"] == "artifact")
    summary_private = next(item for item in summary["outcomes"] if item["event_type"] == "artifact")
    summary_accepted = next(
        item for item in summary["outcomes"] if item["event_type"] == "acceptance"
    )

    assert full["events"][0]["evidence"]["payload"].startswith("private-event-sentinel-")
    assert full["events"][0]["reason"] == "operator-note-sentinel-private"
    assert private_row["evidence_refs"] == outcome["evidence_refs"]
    assert all("evidence" not in item for item in summary["events"])
    assert all("reason" not in item for item in summary["events"])
    assert summary["events"][0]["reason_present"] is True
    assert all("reason_hash" not in item for item in summary["events"])
    assert all("evidence_refs" not in item for item in summary["outcomes"])
    # The acceptance manifest is identities and digests only, so the summary
    # carries the real evidence; the private artifact payload carries none.
    assert summary_private["_promotion_evidence_manifest"] is None
    assert (
        summary_accepted["_promotion_evidence_manifest"]["accepted_outcome_key"]
        == (accepted["accepted_outcome_key"])
    )
    assert summary["events_total_count"] == full["events_total_count"]
    assert summary["outcomes_total_count"] == full["outcomes_total_count"]
    assert promotion_readiness(
        full["worker"],
        full["outcomes"],
        required_successes=1,
    )["verified_artifacts"] == [accepted["artifact_digest"]]
    serialized_summary = json.dumps(summary, separators=(",", ":")).encode("utf-8")
    assert b"private-event-sentinel" not in serialized_summary
    assert b"operator-note-sentinel-private" not in serialized_summary
    assert hashlib.sha256(b"operator-note-sentinel-private").hexdigest().encode() not in (
        serialized_summary
    )
    assert b"private-outcome-sentinel" not in serialized_summary
    with pytest.raises(TypeError, match="include_history_documents"):
        store.get_workforce_worker_detail(
            contractor["worker_id"],
            include_history_documents=1,
        )


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
    replay = store.create_hiring_case(**kwargs)
    assert first["evidence_included"] is True
    assert replay["evidence_included"] is True
    assert replay["id"] == first["id"]
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
    assert store.count_enabled_roster(disabled_agents=()) == 263
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


def test_host_evidenced_acceptance_can_auto_promote_without_changing_identity(
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

    recorded = store.record_accepted_outcome(
        envelope=_acceptance_envelope(contractor, verifier, index=1),
        auto_promote_successes=1,
        disabled_agents=(),
    )

    after = store.get_workforce_worker_detail(
        contractor["worker_id"],
        disabled_agents=(),
    )
    assert recorded["recorded"] is True
    assert recorded["promoted"] is True
    assert after["worker"]["worker_id"] == contractor["worker_id"]
    assert after["worker"]["agent_slug"] == contractor["agent_slug"]
    assert after["worker"]["state"] == "employee"
    assert not after["worker"]["display_label"].startswith("Contractor · ")
    promotion = next(item for item in after["events"] if item["event_type"] == "promote")
    assert promotion["actor"] == "promotion-policy"
    assert promotion["evidence"]["verified_artifacts"] == [recorded["artifact_digest"]]


def test_acceptance_rejects_a_verifier_that_is_the_contractor_itself(tmp_path: Path) -> None:
    """AR-252: a producer judging its own work is not independent verification."""

    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    contractor = store.get_workforce_worker(
        "typescript-application-engineer",
        disabled_agents=(),
    )

    refused = store.record_accepted_outcome(
        envelope=_acceptance_envelope(contractor, contractor, index=1),
        auto_promote_successes=1,
        disabled_agents=(),
    )
    after = store.get_workforce_worker_detail(contractor["worker_id"], disabled_agents=())

    assert refused["recorded"] is False
    assert refused["reason"] == "shared_producer_verifier_identity"
    assert after["worker"]["state"] == "contractor"
    assert after["outcomes"] == []


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
