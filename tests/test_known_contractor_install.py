"""Package authority and idempotent installation for known contractors."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.selector.compatibility import filter_eligible_catalog
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.hiring_contract import CONTRACTOR_PROMPT_TEMPLATE_HASH
from agency_runtime.core.workforce.identity import stable_worker_id
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import (
    PACKAGED_CONTRACTOR_AUTHORITY,
    install_known_contractors,
    known_contractor_package,
    packaged_hiring_evidence,
)


def _contract_hash(value: dict[str, object]) -> str:
    document = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def test_known_contractors_install_atomically_with_truthful_package_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")

    first = install_known_contractors(store)
    second = install_known_contractors(store)

    expected = tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG))
    assert first.installed == expected
    assert first.existing == ()
    assert second.installed == ()
    assert second.existing == expected
    assert store.count_enabled_roster(disabled_agents=()) == len(expected)
    workers = store.list_workforce_workers(state="contractor", limit=20, disabled_agents=())
    assert {item["agent_slug"] for item in workers} == set(expected)
    assert all(item["display_label"].startswith("Contractor · ") for item in workers)
    assert all(item["origin"] == "agency" and item["enabled"] for item in workers)
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    assert snapshot.worker_count == len(expected)
    assert {item.agent_id for item in snapshot.contracts} == set(expected)

    with closing(store._connect()) as conn:
        cases = conn.execute("SELECT * FROM agent_hiring_cases ORDER BY proposed_slug").fetchall()
    assert len(cases) == len(expected)
    for case in cases:
        critic = json.loads(case["critic_evidence"])
        model = json.loads(case["model_evidence"])
        assert case["status"] == "applied"
        assert critic["authority"] == PACKAGED_CONTRACTOR_AUTHORITY
        assert critic["compiler_template_hash"] == CONTRACTOR_PROMPT_TEMPLATE_HASH
        assert model == {
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "inference_required": False,
            "reason": "maintainer-reviewed packaged contractor; no inference call was made",
            "receipts": [],
        }


def test_workforce_slug_batch_is_bounded_canonical_and_rejects_duplicates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    original_connect = store._connect

    assert store.get_workforce_workers_by_slugs((), disabled_agents=()) == {}
    for invalid in ("code-reviewer", b"code-reviewer", {"code-reviewer": True}, iter(())):
        with pytest.raises(TypeError, match="collection of strings"):
            store.get_workforce_workers_by_slugs(invalid, disabled_agents=())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must not contain duplicates"):
        store.get_workforce_workers_by_slugs(
            ("code-reviewer", " CODE-REVIEWER "), disabled_agents=()
        )
    with pytest.raises(ValueError, match="agent slug must be a string"):
        store.get_workforce_workers_by_slugs(("code-reviewer", 7), disabled_agents=())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="agent slug"):
        store.get_workforce_workers_by_slugs(("unsafe') OR 1=1 --",), disabled_agents=())
    with pytest.raises(ValueError, match="at most 64"):
        store.get_workforce_workers_by_slugs(
            tuple(f"worker-{index:02d}" for index in range(65)), disabled_agents=()
        )

    monkeypatch.setattr(
        store,
        "_connect",
        lambda: pytest.fail("invalid or empty batches must not open SQLite"),
    )
    assert store.get_workforce_workers_by_slugs([], disabled_agents=()) == {}
    monkeypatch.setattr(store, "_connect", original_connect)


def test_workforce_slug_batch_returns_existing_missing_and_disabled_projection(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)

    workers = store.get_workforce_workers_by_slugs(
        ("missing-worker", "python-application-engineer", "software-test-engineer"),
        disabled_agents=("software-test-engineer",),
    )

    assert tuple(workers) == ("python-application-engineer", "software-test-engineer")
    assert workers["python-application-engineer"]["state"] == "contractor"
    assert workers["python-application-engineer"]["enabled"] is True
    assert workers["software-test-engineer"]["state"] == "disabled"
    assert workers["software-test-engineer"]["enabled"] is False


def test_workforce_slug_batch_uses_only_parameter_placeholders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    calls: list[tuple[str, tuple[str, ...]]] = []

    class Result:
        @staticmethod
        def fetchall() -> list[object]:
            return []

    class Connection:
        def execute(self, sql: str, parameters: tuple[str, ...]) -> Result:
            calls.append((sql, parameters))
            return Result()

        @staticmethod
        def close() -> None:
            return None

    monkeypatch.setattr(store, "_connect", Connection)

    assert (
        store.get_workforce_workers_by_slugs(
            ("worker.with-dot", "worker-with-dash"), disabled_agents=()
        )
        == {}
    )
    assert calls == [
        (
            "SELECT * FROM agent_workers WHERE agent_slug IN (?,?) ORDER BY agent_slug",
            ("worker-with-dash", "worker.with-dot"),
        )
    ]


def test_noop_known_contractor_install_uses_one_connection_and_one_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    original_connect = store._connect
    connections = 0
    statements: list[str] = []

    def traced_connect() -> Any:
        nonlocal connections
        connections += 1
        connection = original_connect()
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(store, "_connect", traced_connect)

    result = install_known_contractors(store)

    expected = tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG))
    assert result.installed == ()
    assert result.existing == expected
    assert connections == 1
    lookups = [
        statement
        for statement in statements
        if "SELECT * FROM agent_workers WHERE agent_slug IN" in statement
    ]
    assert len(lookups) == 1
    assert lookups[0].count(",") == len(expected) - 1


@pytest.mark.parametrize(
    "worker",
    (
        {"origin": "upstream", "current_hash": "a" * 64},
        {"origin": "agency", "current_hash": "b" * 64},
    ),
)
def test_known_contractor_batch_snapshot_preserves_identity_conflict_failure(
    worker: dict[str, str],
) -> None:
    slug = next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG)))

    class ConflictStore:
        @staticmethod
        def get_workforce_workers_by_slugs(
            _slugs: tuple[str, ...],
            *,
            disabled_agents: tuple[()],
        ) -> dict[str, dict[str, str]]:
            assert disabled_agents == ()
            return {slug: {"agent_slug": slug, **worker}}

        @staticmethod
        def stage_agency_workforce_agent(_agent: object) -> str:
            raise AssertionError("identity conflict must fail before staging")

    with pytest.raises(
        RuntimeError,
        match=f"known contractor identity conflicts with active worker: {slug}",
    ):
        install_known_contractors(ConflictStore())


@pytest.mark.parametrize(
    "snapshot",
    (
        {"unknown-contractor": {"agent_slug": "unknown-contractor"}},
        {next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG))): object()},
        {next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG))): {"agent_slug": "different-contractor"}},
        {
            next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG))).upper(): {
                "agent_slug": next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG))).upper()
            }
        },
    ),
)
def test_known_contractor_install_rejects_unbound_batch_snapshot(
    snapshot: dict[object, object],
) -> None:
    class InvalidBatchStore:
        @staticmethod
        def get_workforce_workers_by_slugs(
            _slugs: tuple[str, ...],
            *,
            disabled_agents: tuple[()],
        ) -> dict[object, object]:
            assert disabled_agents == ()
            return snapshot

    with pytest.raises(RuntimeError, match="known contractor worker snapshot is invalid"):
        install_known_contractors(InvalidBatchStore())


def test_known_contractor_install_retains_legacy_single_worker_reader() -> None:
    slugs = tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG))

    class LegacyStore:
        def __init__(self) -> None:
            self.lookups: list[str] = []

        def get_workforce_worker(
            self,
            slug: str,
            *,
            disabled_agents: tuple[()],
        ) -> dict[str, str]:
            assert disabled_agents == ()
            self.lookups.append(slug)
            package = known_contractor_package(slug)
            return {
                "agent_slug": slug,
                "origin": "agency",
                "current_hash": package.compiled.prompt_hash,
            }

    store = LegacyStore()

    result = install_known_contractors(store)

    assert result.installed == ()
    assert result.existing == slugs
    assert store.lookups == list(slugs)


def test_concurrent_worker_insert_after_batch_snapshot_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    slug = next(iter(sorted(KNOWN_CONTRACTORS_BY_SLUG)))
    original_batch = store.get_workforce_workers_by_slugs

    def racing_batch(
        slugs: tuple[str, ...],
        *,
        disabled_agents: tuple[()],
    ) -> dict[str, dict[str, Any]]:
        snapshot = original_batch(slugs, disabled_agents=disabled_agents)
        with closing(store._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO agent_workers "
                "(worker_id, agent_slug, display_name, origin, employment_class, standing, "
                "current_agent_version_id, current_version, current_hash, revision, "
                "created_at, updated_at) VALUES (?, ?, 'Concurrent worker', 'upstream', "
                "'employee', 'active', ?, ?, ?, 0, ?, ?)",
                (
                    stable_worker_id(slug),
                    slug,
                    str(uuid.uuid4()),
                    "concurrent-v1",
                    "c" * 64,
                    "2026-07-26T00:00:00Z",
                    "2026-07-26T00:00:00Z",
                ),
            )
        return snapshot

    monkeypatch.setattr(store, "get_workforce_workers_by_slugs", racing_batch)

    with pytest.raises(ValueError, match="staged contractor slug already has a workforce identity"):
        install_known_contractors(store)
    worker = original_batch((slug,), disabled_agents=())[slug]
    assert worker["origin"] == "upstream"
    assert worker["current_hash"] == "c" * 64


def test_packaged_contractor_prompt_and_workforce_contract_are_exact_and_routable(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)

    for slug in sorted(KNOWN_CONTRACTORS_BY_SLUG):
        package = known_contractor_package(slug)
        prompt = store.get_specialist_prompt(slug, disabled_agents=())
        worker = store.get_workforce_worker(slug, disabled_agents=())
        assert prompt is not None
        assert prompt["prompt_body"] == package.compiled.prompt
        assert prompt["hash"] == package.compiled.prompt_hash
        assert worker["current_hash"] == package.compiled.prompt_hash
        assert worker["worker_id"] == package.compiled.worker_id


def test_integration_verifier_does_not_require_its_optional_browser_surface() -> None:
    package = known_contractor_package("application-integration-verifier")
    agent = selector_roster_projection(package.agent)

    result = filter_eligible_catalog(
        [agent],
        host="codex",
        platform="windows",
        available_tools={"repository-read", "test-execution"},
        capability_status="native-installation-verified",
    )

    assert [item["agent_slug"] for item in result.eligible] == ["application-integration-verifier"]
    assert "browser" in package.employment_contract.tools
    assert "browser" not in package.agent["required_tools"]
    assert "browser-interaction" in package.agent["tool_affinity"]
    assert "browser-interaction" not in package.workforce_contract.tool_classes
    assert package.workforce_contract.tool_classes == (
        "repository-read",
        "test-execution",
    )


def test_selection_safety_critic_uses_native_runtime_evidence_capability() -> None:
    package = known_contractor_package("selection-safety-critic")

    assert package.agent["required_tools"] == ["workforce-index", "staffing-plan-reader"]
    assert package.workforce_contract.tool_classes == ("runtime-evidence",)


def test_installed_legacy_optional_tool_metadata_is_reconciled_for_routing(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    package = known_contractor_package("application-integration-verifier")
    legacy_agent = {
        **package.agent,
        "required_tools": list(package.employment_contract.tools),
    }
    stale_contract = package.workforce_contract.to_dict()
    stale_contract["tool_classes"] = [
        "browser-interaction",
        "repository-read",
        "test-execution",
    ]
    stale_document = json.dumps(
        stale_contract,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    worker = store.get_workforce_worker(package.employment_contract.slug, disabled_agents=())
    with closing(store._connect()) as conn:
        sequence = int(
            conn.execute(
                "SELECT COALESCE(MAX(projection_sequence), 0) "
                "FROM agent_recruitment_contract_projections"
            ).fetchone()[0]
        )
        conn.execute(
            "UPDATE agent_versions SET metadata = ? WHERE id = ?",
            (
                serialized_revision_metadata(legacy_agent),
                worker["current_agent_version_id"],
            ),
        )
        conn.execute(
            "INSERT INTO agent_recruitment_contract_projections "
            "(id, projection_sequence, worker_id, agent_version_id, "
            "parent_contract_hash, recruitment_contract, recruitment_contract_hash, "
            "projection_authority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, "
            "'test-legacy-package', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (
                str(uuid.uuid4()),
                sequence + 1,
                worker["worker_id"],
                worker["current_agent_version_id"],
                _contract_hash(package.workforce_contract.to_dict()),
                stale_document,
                hashlib.sha256(stale_document.encode("utf-8")).hexdigest(),
            ),
        )
        conn.commit()

    before = next(
        item
        for item in store.get_active_roster_as_catalog(disabled_agents=())
        if item["agent_slug"] == package.employment_contract.slug
    )
    assert "browser-interaction" in before["required_tools"]

    repaired = store.reconcile_packaged_workforce_contracts()

    assert repaired.inspected == len(KNOWN_CONTRACTORS_BY_SLUG)
    assert repaired.updated == 1
    after = next(
        item
        for item in store.get_active_roster_as_catalog(disabled_agents=())
        if item["agent_slug"] == package.employment_contract.slug
    )
    assert after["required_tools"] == ["repository-read", "test-execution"]
    eligible = filter_eligible_catalog(
        [after],
        host="codex",
        platform="windows",
        available_tools={"repository-read", "test-execution"},
        capability_status="native-installation-verified",
    )
    assert [item["agent_slug"] for item in eligible.eligible] == [
        "application-integration-verifier"
    ]


def test_packaged_authority_rejects_tampered_or_unknown_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    package = known_contractor_package("python-application-engineer")
    evidence = packaged_hiring_evidence(package)
    evidence["model_evidence"]["reason"] = "pretend model evidence"
    contract = package.workforce_contract.to_dict()
    case = store.create_hiring_case(
        case_type="hire",
        proposed_slug=package.employment_contract.slug,
        work_unit_id=str(uuid.uuid4()),
        request_hash="a" * 64,
        contract_evidence=contract,
        contract_hash=_contract_hash(contract),
        **evidence,
    )

    with pytest.raises(ValueError, match="validated critic and model evidence"):
        store.transition_hiring_case(case["id"], status="audited")

    unknown_contract = {**contract, "agent_id": "unknown-contractor"}
    unknown_contract["worker_id"] = "unknown-worker"
    with pytest.raises(ValueError, match="validated critic and model evidence"):
        unknown = store.create_hiring_case(
            case_type="hire",
            proposed_slug="unknown-contractor",
            work_unit_id=str(uuid.uuid4()),
            request_hash="b" * 64,
            contract_evidence=unknown_contract,
            contract_hash=_contract_hash(unknown_contract),
            **packaged_hiring_evidence(package),
        )
        store.transition_hiring_case(unknown["id"], status="audited")


def test_an_amended_packaged_worker_is_reported_as_divergent_and_left_alone(
    tmp_path: Path,
) -> None:
    """Rule 6: repair must stop at an amendment, and must no longer stop silently.

    ``reconcile_packaged_workforce_contracts`` deliberately refuses to re-project a
    worker whose active revision is not the packaged one -- overwriting a
    deliberate amendment would be far worse than leaving it. What was missing is
    that the refusal produced no evidence at all, so a contractor amending an
    ``origin=upstream`` worker was invisible.
    """

    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    slug = "application-integration-verifier"
    package = known_contractor_package(slug)
    worker = store.get_workforce_worker(slug, disabled_agents=())
    amended_body = str(package.agent["prompt_body"]) + "\n\nAmended locally by an operator."

    with closing(store._connect()) as conn:
        conn.execute(
            "UPDATE agent_versions SET content = ? WHERE id = ?",
            (amended_body, worker["current_agent_version_id"]),
        )
        conn.commit()

    result = store.reconcile_packaged_workforce_contracts()

    reported = {item.agent_slug: item for item in result.divergent}
    assert slug in reported, "an amended packaged worker produced no divergence evidence"
    assert reported[slug].reason == "revision_modified"
    assert reported[slug].expected_origin == reported[slug].actual_origin
    assert reported[slug].to_dict()["agent_slug"] == slug

    # The amendment survives: this surface reports, it never repairs or reverts.
    with closing(store._connect()) as conn:
        stored = conn.execute(
            "SELECT content FROM agent_versions WHERE id = ?",
            (worker["current_agent_version_id"],),
        ).fetchone()
    assert str(stored["content"]) == amended_body

    # And the amended worker is excluded from the repaired population rather than
    # counted as inspected-and-clean.
    assert result.inspected == len(KNOWN_CONTRACTORS_BY_SLUG) - 1


def test_a_clean_packaged_roster_reports_no_divergence(tmp_path: Path) -> None:
    """The evidence must stay quiet when nothing has been amended."""

    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)

    result = store.reconcile_packaged_workforce_contracts()

    assert result.divergent == ()
    assert result.inspected == len(KNOWN_CONTRACTORS_BY_SLUG)
