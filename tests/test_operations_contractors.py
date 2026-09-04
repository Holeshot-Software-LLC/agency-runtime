"""AR-370 criterion 1: the operational verbs have a packaged specialist to find.

The routing corpus (``core/evals/data/routing_v1.py``) described a service
operations engineer and a monitoring engineer as eval fixtures only; the live
roster carried neither, so ``configure the gateway`` and ``install this: <url>``
scored 0.0 against every contract and fell back to slug order. These two
contracts are authored through the ``agency-runtime`` packaged source so an
install puts them into the live roster.
"""

from __future__ import annotations

import pytest

from agency_runtime.core.routing_snapshot import capture_routing_snapshot
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import (
    install_known_contractors,
    known_contractor_package,
)

OPERATIONS_SLUGS = ("service-operations-engineer", "monitoring-engineer")

# One work statement per operational verb, phrased the way the runtime
# retrieves once the inferred subject has run (ADR-0197, ADR-0208).
WORK_STATEMENTS = (
    (
        "Install the CLI tool at https://example.test/dist on this linux host",
        "service-operations-engineer",
    ),
    (
        "Install a command line tool on this linux host and verify it runs",
        "service-operations-engineer",
    ),
    ("Configure the api gateway service and validate the change", "service-operations-engineer"),
    ("Restart the dashboard service and confirm it is reachable", "service-operations-engineer"),
    ("Upgrade the deployed runtime to the latest release", "service-operations-engineer"),
    ("Troubleshoot why the service will not start on this host", "service-operations-engineer"),
    ("Set up monitoring and alerting for the newly provisioned host", "monitoring-engineer"),
)


@pytest.fixture(scope="module")
def catalog(tmp_path_factory: pytest.TempPathFactory) -> list[dict]:
    store = Store(tmp_path_factory.mktemp("ops") / "agency.db")
    result = install_known_contractors(store)
    assert set(OPERATIONS_SLUGS) <= set(result.installed)
    # The same catalog `agency search` and the runtime's recall run on.
    return list(capture_routing_snapshot(store).catalog)


def test_both_operations_contracts_are_packaged_with_the_operations_domain() -> None:
    for slug in OPERATIONS_SLUGS:
        package = known_contractor_package(slug)
        assert package.agent["domains"] == ["operations"]
        assert "operations" in package.agent["categories"]
        assert package.agent["authority"] == "modify"
        assert "implementation-change" in package.agent["artifact_kinds"]


def test_service_operations_engineer_is_eligible_wherever_the_installer_engineer_is() -> None:
    operations = known_contractor_package("service-operations-engineer").agent
    installer = known_contractor_package("cross-platform-installer-engineer").agent
    assert set(operations["required_tools"]) == set(installer["required_tools"])


def test_monitoring_surface_is_affinity_not_an_eligibility_gate() -> None:
    package = known_contractor_package("monitoring-engineer")
    assert "monitoring" in package.employment_contract.tools
    assert "monitoring" not in package.agent["required_tools"]
    assert "monitoring-observability" in package.agent["tool_affinity"]


@pytest.mark.parametrize(("statement", "expected"), WORK_STATEMENTS)
def test_each_operational_verb_retrieves_its_specialist_first(
    catalog: list[dict], statement: str, expected: str
) -> None:
    candidates, scores = pre_narrow(statement, catalog, limit=3)
    ranked = [item.get("slug") or item.get("agent_slug") for item in candidates]
    assert ranked[0] == expected, (statement, list(zip(ranked, scores, strict=True)))
    assert scores[0] > 0.0


def test_runbook_authoring_does_not_land_on_the_monitoring_engineer(catalog: list[dict]) -> None:
    candidates, scores = pre_narrow(
        "Write a runbook for responding to a p95 latency alert", catalog, limit=3
    )
    ranked = [item.get("slug") or item.get("agent_slug") for item in candidates]
    assert ranked[:1] != ["monitoring-engineer"], list(zip(ranked, scores, strict=True))


def test_the_contracts_name_the_corpus_verbs_in_their_capabilities() -> None:
    operations = KNOWN_CONTRACTORS_BY_SLUG["service-operations-engineer"]
    text = " ".join((*operations.capabilities, *operations.outcomes_owned)).casefold()
    for verb in ("install", "configure", "restart", "upgrade", "troubleshoot", "provision"):
        assert verb in text, verb
    monitoring = KNOWN_CONTRACTORS_BY_SLUG["monitoring-engineer"]
    text = " ".join((*monitoring.capabilities, *monitoring.outcomes_owned)).casefold()
    for noun in ("monitoring", "alerting", "metrics", "dashboard"):
        assert noun in text, noun
