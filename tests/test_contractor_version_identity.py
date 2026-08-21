"""Both contractor registration paths must mint one identical version.

A contractor is looked up by (slug, version, hash) against agent_versions and
agent_active.  When the packaged installer and the dynamic hiring path spell
the same prompt's version differently, a contractor registered by one is
unresolvable by a reference minted by the other, and preflight fails closed in
specialist_context on a specialist that appears not to be registered at all --
which blocks the user's prompt outright.

The historical defect: known_installer truncated the raw prompt hash without
stripping its "sha256:" prefix, so it minted "contractor-1-sha256:e70b4c2b"
where hiring minted "contractor-1-e70b4c2badd48f1f" for identical content.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from agency_runtime.core.workforce.hiring import _agent_document
from agency_runtime.core.workforce.hiring_contract import (
    CONTRACTOR_PROMPT_TEMPLATE_VERSION,
    compile_contractor,
    contractor_prompt_version,
)
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import known_contractor_agent

_SAMPLE_SLUGS = sorted(KNOWN_CONTRACTORS_BY_SLUG)[:6]


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_both_registration_paths_mint_identical_versions(slug: str) -> None:
    contract = KNOWN_CONTRACTORS_BY_SLUG[slug]

    packaged = known_contractor_agent(contract)
    hired = _agent_document(contract, domains=("software-engineering",), stacks=())

    assert packaged["version"] == hired["version"], (
        "packaged and dynamically hired registrations disagree on version; a "
        "contractor registered by one path is unresolvable by the other"
    )


@pytest.mark.parametrize("slug", _SAMPLE_SLUGS)
def test_minted_version_is_derived_from_the_stored_prompt_hash(slug: str) -> None:
    """The version must be recomputable from the row's own hash column."""

    contract = KNOWN_CONTRACTORS_BY_SLUG[slug]
    agent = known_contractor_agent(contract)

    assert agent["version"] == contractor_prompt_version(agent["hash"])


def test_version_strips_the_algorithm_prefix() -> None:
    digest = "e70b4c2badd48f1f" + "0" * 48

    assert (
        contractor_prompt_version(f"sha256:{digest}")
        == f"contractor-{CONTRACTOR_PROMPT_TEMPLATE_VERSION}-e70b4c2badd48f1f"
    )


def test_prefixed_digest_can_no_longer_be_minted() -> None:
    """The historical defect: 'sha256:' leaking into the version token."""

    version = contractor_prompt_version("sha256:" + "a" * 64)

    assert "sha256:" not in version.removeprefix("contractor-")
    assert ":" not in version


@pytest.mark.parametrize(
    "prompt_hash",
    ["", None, "sha256:", "sha256:NOTHEXVALUE00000", "abc123", "sha256:" + "A" * 64],
)
def test_malformed_prompt_hashes_are_rejected_rather_than_truncated(prompt_hash: object) -> None:
    """Minting an unmatchable identity must fail loudly at the source."""

    with pytest.raises(ValueError):
        contractor_prompt_version(prompt_hash)  # type: ignore[arg-type]


def test_compiled_contractor_hash_round_trips_through_the_helper() -> None:
    contract = KNOWN_CONTRACTORS_BY_SLUG[_SAMPLE_SLUGS[0]]
    compiled = compile_contractor(contract)

    assert compiled.prompt_hash.startswith("sha256:")
    assert (
        contractor_prompt_version(
            compiled.prompt_hash,
            template_version=compiled.template_version,
        )
        == known_contractor_agent(contract)["version"]
    )


def test_legacy_prompt_identity_requires_its_recorded_template_version() -> None:
    current = KNOWN_CONTRACTORS_BY_SLUG["typescript-application-engineer"]
    legacy = replace(current, schema_version=1, execution_profile=None)
    compiled = compile_contractor(legacy)

    assert contractor_prompt_version(
        compiled.prompt_hash,
        template_version=compiled.template_version,
    ).startswith("contractor-1-")
