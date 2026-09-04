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

from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.known_contractors import (
    KNOWN_CONTRACTOR_CONTRACTS,
    KNOWN_CONTRACTORS_BY_SLUG,
)
from agency_runtime.core.workforce.known_installer import (
    install_known_contractors,
    known_contractor_agent,
    known_contractor_package,
)

OPERATIONS_SLUGS = ("service-operations-engineer", "monitoring-engineer")

# One work statement per operational verb, phrased the way the runtime
# retrieves once the inferred subject has run (ADR-0197, ADR-0208), with the
# rank each specialist holds on the FULL packaged roster. The distribution-url
# phrasing is the one case an upstream card outscores: `tool-evaluator` reads
# the tool/host language at 19.5 against 12.0, so the honest guarantee there is
# top-three until the recruiter's typed coverage decides.
WORK_STATEMENTS = (
    (
        "Install the CLI tool at https://example.test/dist on this linux host",
        "service-operations-engineer",
        3,
    ),
    (
        "Install a command line tool on this linux host and verify it runs",
        "service-operations-engineer",
        1,
    ),
    ("Configure the api gateway service and validate the change", "service-operations-engineer", 1),
    ("Restart the dashboard service and confirm it is reachable", "service-operations-engineer", 1),
    ("Upgrade the deployed runtime to the latest release", "service-operations-engineer", 1),
    ("Troubleshoot why the service will not start on this host", "service-operations-engineer", 1),
    ("Set up monitoring and alerting for the newly provisioned host", "monitoring-engineer", 1),
)


@pytest.fixture(scope="module")
def catalog() -> list[dict]:
    """The full packaged roster, projected the way the store serves recall.

    A fixture holding only the 17 packaged contractors ranks these specialists
    first trivially and can never detect an upstream card outscoring them; the
    bundled cards are what they compete with on a live roster.
    """

    agents = [
        *BundledRoster(),
        *(known_contractor_agent(contract) for contract in KNOWN_CONTRACTOR_CONTRACTS),
    ]
    return [selector_roster_projection(agent) for agent in agents]


def test_the_catalog_is_the_full_packaged_roster(catalog: list[dict]) -> None:
    assert len(catalog) == len(BundledRoster()) + len(KNOWN_CONTRACTOR_CONTRACTS)
    slugs = {item["agent_slug"] for item in catalog}
    assert set(OPERATIONS_SLUGS) <= slugs
    assert "tool-evaluator" in slugs


def test_install_adds_both_contracts_to_a_fresh_store(tmp_path) -> None:
    result = install_known_contractors(Store(tmp_path / "agency.db"))
    assert set(OPERATIONS_SLUGS) <= set(result.installed)


def test_both_operations_contracts_are_packaged_with_the_operations_domain() -> None:
    for slug in OPERATIONS_SLUGS:
        package = known_contractor_package(slug)
        assert package.agent["domains"] == ["operations"]
        assert "operations" in package.agent["categories"]
        assert package.agent["authority"] == "modify"
        assert "implementation-change" in package.agent["artifact_kinds"]


def test_service_operations_engineer_requires_the_installer_engineers_tools() -> None:
    """Tool parity is necessary for shared eligibility, not sufficient.

    The domain axis still differs: on a software-engineering unit the installer
    engineer is eligible and this contract reads `agent_domain_mismatch`.
    """

    operations = known_contractor_package("service-operations-engineer").agent
    installer = known_contractor_package("cross-platform-installer-engineer").agent
    assert set(operations["required_tools"]) == set(installer["required_tools"])


def test_monitoring_surface_is_affinity_not_an_eligibility_gate() -> None:
    package = known_contractor_package("monitoring-engineer")
    assert "monitoring" in package.employment_contract.tools
    assert "monitoring" not in package.agent["required_tools"]
    assert "monitoring-observability" in package.agent["tool_affinity"]


@pytest.mark.parametrize(("statement", "expected", "max_rank"), WORK_STATEMENTS)
def test_each_operational_verb_retrieves_its_specialist(
    catalog: list[dict], statement: str, expected: str, max_rank: int
) -> None:
    candidates, scores = pre_narrow(statement, catalog, limit=3)
    ranked = [item["agent_slug"] for item in candidates]
    assert expected in ranked[:max_rank], (statement, list(zip(ranked, scores, strict=True)))
    assert scores[ranked.index(expected)] > 0.0


def test_runbook_authoring_does_not_land_on_the_monitoring_engineer(catalog: list[dict]) -> None:
    candidates, scores = pre_narrow(
        "Write a runbook for responding to a p95 latency alert", catalog, limit=3
    )
    ranked = [item["agent_slug"] for item in candidates]
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
